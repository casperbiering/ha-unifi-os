"""Test UniFi OS update entities."""

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from homeassistant.components.update import (
    ATTR_INSTALLED_VERSION,
    ATTR_LATEST_VERSION,
    UpdateEntityFeature,
)
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import CONSOLE_MAC, DOMAIN

OS_ENTITY = "update.udm_se_firmware"
NETWORK_ENTITY = "update.udm_se_unifi_network_application"
PROTECT_ENTITY = "update.udm_se_unifi_protect_application"

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.mark.usefixtures("init_integration")
async def test_update_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test UniFi OS is current, Network has an update, and Protect is absent."""
    os_state = hass.states.get(OS_ENTITY)
    assert os_state is not None
    assert os_state.state == STATE_OFF
    assert os_state.attributes[ATTR_INSTALLED_VERSION] == "5.1.31"
    assert os_state.attributes[ATTR_LATEST_VERSION] == "5.1.31"
    assert os_state.attributes["supported_features"] == UpdateEntityFeature(0)

    network_state = hass.states.get(NETWORK_ENTITY)
    assert network_state is not None
    assert network_state.state == STATE_ON
    assert network_state.attributes[ATTR_INSTALLED_VERSION] == "10.5.67"
    assert network_state.attributes[ATTR_LATEST_VERSION] == "10.6.101"
    assert network_state.attributes["release_channel"] == "release"
    assert network_state.attributes["supported_features"] == UpdateEntityFeature(0)

    assert hass.states.get(PROTECT_ENTITY) is None

    os_entry = entity_registry.async_get(OS_ENTITY)
    assert os_entry is not None
    assert os_entry.unique_id == f"unifi_os-{CONSOLE_MAC}"
    assert os_entry.original_name == "Firmware"
    assert os_entry.entity_category is EntityCategory.CONFIG

    network_entry = entity_registry.async_get(NETWORK_ENTITY)
    assert network_entry is not None
    assert network_entry.unique_id == f"unifi_app-{CONSOLE_MAC}-network"
    assert network_entry.original_name == "UniFi Network Application"
    assert network_entry.entity_category is EntityCategory.CONFIG

    console = device_registry.async_get_device_by_connection(
        (dr.CONNECTION_NETWORK_MAC, CONSOLE_MAC), mock_config_entry.entry_id
    )
    assert console is not None
    assert console.name == "UDM SE"
    assert console.model == "UDMPROSE"
    assert os_entry.device_id == console.id
    assert network_entry.device_id == console.id
    assert entity_registry.async_get(PROTECT_ENTITY) is None
    assert (
        len(
            dr.async_entries_for_config_entry(
                device_registry, mock_config_entry.entry_id
            )
        )
        == 1
    )


@pytest.mark.usefixtures("init_integration")
async def test_update_entities_unavailable(
    hass: HomeAssistant,
    mock_unifi_os_requests: Callable[..., None],
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test update entities go unavailable when the console cannot be reached."""
    assert hass.states.get(OS_ENTITY).state == STATE_OFF
    assert hass.states.get(NETWORK_ENTITY).state == STATE_ON

    aioclient_mock.clear_requests()
    mock_unifi_os_requests(system_status=500)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=30))
    await hass.async_block_till_done()

    assert hass.states.get(OS_ENTITY).state == STATE_UNAVAILABLE
    assert hass.states.get(NETWORK_ENTITY).state == STATE_UNAVAILABLE


async def test_os_update_available(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_unifi_os_requests: Callable[..., None],
    system_payload: dict[str, Any],
) -> None:
    """Test the UniFi OS entity when an OS update is available."""
    console = system_payload["devices"]["unifiOS"][0]
    console["firmwareStatus"] = "updateAvailable"
    system_payload["firmware"]["latest"]["version"] = "v5.2.0+abc123"

    mock_unifi_os_requests(system=system_payload)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    os_state = hass.states.get(OS_ENTITY)
    assert os_state is not None
    assert os_state.state == STATE_ON
    assert os_state.attributes[ATTR_INSTALLED_VERSION] == "5.1.31"
    assert os_state.attributes[ATTR_LATEST_VERSION] == "5.2.0"


async def test_legacy_application_devices_removed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_unifi_os_requests: Callable[..., None],
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test leftover per-app service devices are removed on setup."""
    mock_config_entry.add_to_hass(hass)
    leftover = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        entry_type=dr.DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, f"{CONSOLE_MAC}-network")},
        name="UniFi Network Application",
    )
    mock_unifi_os_requests()
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert device_registry.async_get(leftover.id) is None
    assert (
        len(
            dr.async_entries_for_config_entry(
                device_registry, mock_config_entry.entry_id
            )
        )
        == 1
    )
