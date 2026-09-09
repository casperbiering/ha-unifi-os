"""Config flow for the UniFi OS integration."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.device_registry import format_mac

from .api import async_get_controller, async_get_system
from .const import DEFAULT_PORT, DEFAULT_VERIFY_SSL, DOMAIN
from .errors import AuthenticationRequired, CannotConnect, NotUnifiOs
from .models import parse_system

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class UnifiOsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a UniFi OS config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                title, unique_id = await self._async_validate(user_input)
            except AuthenticationRequired:
                errors["base"] = "faulty_credentials"
            except CannotConnect:
                errors["base"] = "service_unavailable"
            except NotUnifiOs:
                errors["base"] = "not_unifi_os"
            else:
                await self.async_set_unique_id(unique_id)
                if self.source == SOURCE_REAUTH:
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data_updates=user_input,
                    )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)

        schema = STEP_USER_DATA_SCHEMA
        if self.source == SOURCE_REAUTH:
            schema = self.add_suggested_values_to_schema(
                schema, self._get_reauth_entry().data
            )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Trigger a reauthentication flow."""
        reauth_entry = self._get_reauth_entry()
        self.context["title_placeholders"] = {
            CONF_HOST: reauth_entry.data[CONF_HOST],
            CONF_NAME: reauth_entry.title,
        }
        return await self.async_step_user()

    async def _async_validate(self, user_input: dict[str, Any]) -> tuple[str, str]:
        """Validate credentials and return title and unique id."""
        api = await async_get_controller(self.hass, MappingProxyType(user_input))
        system = parse_system(await async_get_system(api))
        return system.os.name, format_mac(system.os.mac)
