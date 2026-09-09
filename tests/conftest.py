"""Fixtures for UniFi OS tests."""

import json
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONTENT_TYPE_JSON,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

pytest_plugins = ("pytest_homeassistant_custom_component",)

import custom_components

_REPO_CC = str(Path(__file__).resolve().parent.parent / "custom_components")
if _REPO_CC not in custom_components.__path__:
    custom_components.__path__.insert(0, _REPO_CC)

DOMAIN = "unifi_os"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_PORT = 443
CONSOLE_MAC = "00:de:ad:00:be:ef"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

USER_INPUT = {
    CONF_HOST: DEFAULT_HOST,
    CONF_USERNAME: "username",
    CONF_PASSWORD: "password",
    CONF_PORT: DEFAULT_PORT,
    CONF_VERIFY_SSL: False,
}


@pytest.fixture(autouse=True)
def enable_unifi_os_custom_component(enable_custom_integrations: None) -> None:
    """Discover the UniFi OS custom integration for every test."""


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Skip setting up the config entry during config flow tests."""
    with patch("custom_components.unifi_os.async_setup_entry", return_value=True):
        yield


@pytest.fixture
def system_payload() -> dict[str, Any]:
    """Return the slim GET /api/system fixture."""
    return json.loads((FIXTURES_DIR / "system.json").read_text(encoding="utf-8"))


@pytest.fixture
def mock_unifi_os_requests(
    aioclient_mock: AiohttpClientMocker, system_payload: dict[str, Any]
) -> Callable[..., None]:
    """Mock UniFi OS login and GET /api/system."""

    def _mock(
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        unifi_os: bool = True,
        login_status: int = 200,
        system: dict[str, Any] | None = None,
        system_status: int = 200,
    ) -> None:
        url = f"https://{host}:{port}"
        aioclient_mock.get(url, status=200 if unifi_os else 302)
        if unifi_os:
            aioclient_mock.post(
                f"{url}/api/auth/login",
                status=login_status,
                json={"unique_id": "user-id", "username": "username"},
                headers={"content-type": CONTENT_TYPE_JSON},
            )
        else:
            aioclient_mock.post(
                f"{url}/api/login",
                status=login_status,
                json={"data": "login successful", "meta": {"rc": "ok"}},
                headers={"content-type": CONTENT_TYPE_JSON},
            )
        aioclient_mock.get(
            f"{url}/api/system",
            status=system_status,
            json=system if system is not None else system_payload,
            headers={"content-type": CONTENT_TYPE_JSON},
        )

    return _mock


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a UniFi OS config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Dream Machine",
        unique_id=CONSOLE_MAC,
        data=USER_INPUT,
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_unifi_os_requests: Callable[..., None],
    enable_unifi_os_custom_component: None,
) -> MockConfigEntry:
    """Set up the UniFi OS integration."""
    mock_unifi_os_requests()
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
