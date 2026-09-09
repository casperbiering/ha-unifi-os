"""The UniFi OS integration."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .api import async_get_controller
from .const import ATTR_MANUFACTURER, DOMAIN, PLATFORMS
from .coordinator import UnifiOsConfigEntry, UnifiOsCoordinator
from .errors import AuthenticationRequired, CannotConnect, NotUnifiOs

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the UniFi OS integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: UnifiOsConfigEntry) -> bool:
    """Set up UniFi OS from a config entry."""
    try:
        api = await async_get_controller(hass, entry.data)
    except CannotConnect as err:
        raise ConfigEntryNotReady from err
    except (AuthenticationRequired, NotUnifiOs) as err:
        raise ConfigEntryAuthFailed from err

    coordinator = UnifiOsCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    mac = _async_register_console_device(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_remove_legacy_application_devices(hass, entry, mac)
    return True


def _async_register_console_device(
    hass: HomeAssistant, entry: UnifiOsConfigEntry
) -> str:
    """Register the UniFi OS console device and return its formatted MAC."""
    os_info = entry.runtime_data.data.os
    mac = dr.format_mac(os_info.mac)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        configuration_url=entry.runtime_data.configuration_url,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        identifiers={(DOMAIN, mac)},
        manufacturer=ATTR_MANUFACTURER,
        model=os_info.shortname,
        name=os_info.model,
        sw_version=os_info.firmware,
    )
    return mac


def _async_remove_legacy_application_devices(
    hass: HomeAssistant, entry: UnifiOsConfigEntry, mac: str
) -> None:
    """Remove per-app service devices from the first layout."""
    device_registry = dr.async_get(hass)
    console_identifier = (DOMAIN, mac)
    console_connection = (dr.CONNECTION_NETWORK_MAC, mac)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if (
            console_identifier in device.identifiers
            or console_connection in device.connections
        ):
            continue
        device_registry.async_remove_device(device.id)


async def async_unload_entry(hass: HomeAssistant, entry: UnifiOsConfigEntry) -> bool:
    """Unload a UniFi OS config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
