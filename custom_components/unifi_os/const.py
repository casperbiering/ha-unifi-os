"""Constants for the UniFi OS integration."""

import logging
from datetime import timedelta

from homeassistant.const import Platform

LOGGER = logging.getLogger(__package__)
DOMAIN = "unifi_os"

PLATFORMS = [Platform.UPDATE]

SCAN_INTERVAL = timedelta(minutes=30)

DEFAULT_PORT = 443
DEFAULT_VERIFY_SSL = False

ATTR_MANUFACTURER = "Ubiquiti"

APP_TITLES = {
    "access": "UniFi Access Application",
    "connect": "UniFi Connect Application",
    "innerspace": "UniFi Innerspace Application",
    "network": "UniFi Network Application",
    "protect": "UniFi Protect Application",
    "talk": "UniFi Talk Application",
}

FIRMWARE_STATUS_UPDATE_AVAILABLE = "updateAvailable"
UPDATE_STATE_NOT_STARTED = "NOT_STARTED"
PROGRESS_IN_PROGRESS = frozenset(
    {"downloading", "download", "installing", "updating", "in_progress"}
)
