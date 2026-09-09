"""Status-only update entities for UniFi OS and installed applications."""

from typing import override

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import APP_TITLES, ATTR_MANUFACTURER, DOMAIN
from .coordinator import UnifiOsConfigEntry, UnifiOsCoordinator
from .models import UnifiAppInfo

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UnifiOsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up UniFi OS update entities."""
    coordinator = entry.runtime_data
    os_added = False
    known_apps: set[str] = set()

    @callback
    def _async_add_update_entities() -> None:
        nonlocal os_added
        entities: list[UpdateEntity] = []
        if not os_added:
            entities.append(UnifiOsUpdateEntity(coordinator))
            os_added = True
        for app in coordinator.data.apps:
            if app.name in known_apps:
                continue
            entities.append(UnifiAppUpdateEntity(coordinator, app.name))
            known_apps.add(app.name)
        if entities:
            async_add_entities(entities)

    _async_add_update_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_update_entities))


def _console_device_info(coordinator: UnifiOsCoordinator) -> DeviceInfo:
    """Return device info for the UniFi OS console."""
    os_info = coordinator.data.os
    mac = dr.format_mac(os_info.mac)
    return DeviceInfo(
        configuration_url=coordinator.configuration_url,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        identifiers={(DOMAIN, mac)},
        manufacturer=ATTR_MANUFACTURER,
        model=os_info.shortname,
        name=os_info.model,
        sw_version=os_info.firmware,
    )


class UnifiOsUpdateEntity(CoordinatorEntity[UnifiOsCoordinator], UpdateEntity):
    """UniFi OS firmware update status."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_translation_key = "firmware"

    def __init__(self, coordinator: UnifiOsCoordinator) -> None:
        """Initialize the UniFi OS update entity."""
        super().__init__(coordinator)
        mac = dr.format_mac(coordinator.data.os.mac)
        self._attr_unique_id = f"unifi_os-{mac}"
        self._attr_device_info = _console_device_info(coordinator)

    @property
    @override
    def installed_version(self) -> str:
        """Return the installed UniFi OS version."""
        return self.coordinator.data.os.firmware

    @property
    @override
    def latest_version(self) -> str:
        """Return the latest UniFi OS version."""
        return self.coordinator.data.os.latest_version

    @property
    @override
    def in_progress(self) -> bool:
        """Return whether a UniFi OS update is running."""
        return self.coordinator.data.os.in_progress


class UnifiAppUpdateEntity(CoordinatorEntity[UnifiOsCoordinator], UpdateEntity):
    """Installed UniFi application update status."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(self, coordinator: UnifiOsCoordinator, app_name: str) -> None:
        """Initialize an application update entity."""
        super().__init__(coordinator)
        self._app_name = app_name
        if app_name in APP_TITLES:
            self._attr_translation_key = app_name
        else:
            self._attr_name = app_name
        mac = dr.format_mac(coordinator.data.os.mac)
        self._attr_unique_id = f"unifi_app-{mac}-{app_name}"
        self._attr_device_info = _console_device_info(coordinator)

    @property
    def _app(self) -> UnifiAppInfo | None:
        """Return the current application record, if still installed."""
        return self.coordinator.data.get_app(self._app_name)

    @property
    @override
    def available(self) -> bool:
        """Return whether the application is still installed and reachable."""
        return super().available and self._app is not None

    @property
    @override
    def installed_version(self) -> str | None:
        """Return the installed application version."""
        if (app := self._app) is None:
            return None
        return app.version

    @property
    @override
    def latest_version(self) -> str | None:
        """Return the latest application version."""
        if (app := self._app) is None:
            return None
        return app.latest_version

    @property
    @override
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the application release channel."""
        if (app := self._app) is None:
            return None
        return {"release_channel": app.release_channel}
