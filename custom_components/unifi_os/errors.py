"""Errors for the UniFi OS integration."""

from homeassistant.exceptions import HomeAssistantError


class UnifiOsError(HomeAssistantError):
    """Base class for UniFi OS exceptions."""


class AuthenticationRequired(UnifiOsError):
    """Authentication failed or session expired."""


class CannotConnect(UnifiOsError):
    """Unable to connect to the UniFi OS console."""


class NotUnifiOs(UnifiOsError):
    """Host is not a UniFi OS console."""
