"""Parsed UniFi OS system payload."""

from dataclasses import dataclass
from typing import Any

from .const import (
    FIRMWARE_STATUS_UPDATE_AVAILABLE,
    PROGRESS_IN_PROGRESS,
    UPDATE_STATE_NOT_STARTED,
)


def normalize_version(version: str) -> str:
    """Strip leading v and +build suffix from a UniFi version string."""
    cleaned = version.removeprefix("v").removeprefix("V")
    return cleaned.split("+", 1)[0]


def _os_in_progress(firmware: dict[str, Any]) -> bool:
    """Return whether a UniFi OS update is currently running."""
    update = firmware.get("update") or {}
    progress = firmware.get("progress") or {}
    state = update.get("state")
    if state is not None and state != UPDATE_STATE_NOT_STARTED:
        return True
    return progress.get("state") in PROGRESS_IN_PROGRESS


@dataclass(frozen=True)
class UnifiOsInfo:
    """UniFi OS console update state."""

    mac: str
    name: str
    model: str
    shortname: str
    firmware: str
    firmware_status: str
    latest_version: str
    in_progress: bool


@dataclass(frozen=True)
class UnifiAppInfo:
    """Installed UniFi application update state."""

    name: str
    version: str
    update_available: str | None
    release_channel: str
    updatable: bool

    @property
    def latest_version(self) -> str:
        """Latest available version, or the installed version if none."""
        return self.update_available or self.version


@dataclass(frozen=True)
class UnifiOsSystem:
    """Parsed GET /api/system payload."""

    os: UnifiOsInfo
    apps: tuple[UnifiAppInfo, ...]

    def get_app(self, name: str) -> UnifiAppInfo | None:
        """Return an installed application by name."""
        return next((app for app in self.apps if app.name == name), None)


def parse_system(raw: dict[str, Any]) -> UnifiOsSystem:
    """Parse a GET /api/system payload into OS and installed apps."""
    consoles = raw["devices"]["unifiOS"]
    if not consoles:
        raise ValueError("GET /api/system had no UniFi OS console")

    console = consoles[0]
    firmware = raw["firmware"]
    installed = console["firmware"]
    catalog = normalize_version(firmware["latest"]["version"])
    status = console["firmwareStatus"]
    latest = (
        catalog
        if status == FIRMWARE_STATUS_UPDATE_AVAILABLE or catalog != installed
        else installed
    )

    os_info = UnifiOsInfo(
        mac=console["mac"],
        name=console["name"],
        model=console["model"],
        shortname=console["shortname"],
        firmware=installed,
        firmware_status=status,
        latest_version=latest,
        in_progress=_os_in_progress(firmware),
    )

    apps = tuple(
        UnifiAppInfo(
            name=controller["name"],
            version=controller["version"],
            update_available=controller["updateAvailable"],
            release_channel=controller["releaseChannel"],
            updatable=controller["updatable"],
        )
        for controller in raw["apps"]["controllers"]
        if controller["isInstalled"]
    )
    return UnifiOsSystem(os=os_info, apps=apps)
