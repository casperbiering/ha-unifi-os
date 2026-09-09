"""Data update coordinator for UniFi OS."""

import aiounifi
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import async_get_system
from .const import DEFAULT_PORT, DOMAIN, LOGGER, SCAN_INTERVAL
from .errors import AuthenticationRequired, CannotConnect
from .models import UnifiOsSystem, parse_system

type UnifiOsConfigEntry = ConfigEntry[UnifiOsCoordinator]


class UnifiOsCoordinator(DataUpdateCoordinator[UnifiOsSystem]):
    """Poll GET /api/system for OS and application updates."""

    config_entry: UnifiOsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: UnifiOsConfigEntry,
        api: aiounifi.Controller,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    @property
    def configuration_url(self) -> str:
        """Return the local UniFi OS configuration URL."""
        host: str = self.config_entry.data[CONF_HOST]
        port: int = self.config_entry.data[CONF_PORT]
        if port == DEFAULT_PORT:
            return f"https://{host}"
        return f"https://{host}:{port}"

    async def _async_update_data(self) -> UnifiOsSystem:
        """Fetch and parse the system payload."""
        try:
            raw = await async_get_system(self.api)
        except AuthenticationRequired as err:
            raise ConfigEntryAuthFailed from err
        except CannotConnect as err:
            raise UpdateFailed("Unable to reach UniFi OS") from err

        try:
            return parse_system(raw)
        except (KeyError, ValueError, TypeError) as err:
            raise UpdateFailed("Unexpected UniFi OS system payload") from err
