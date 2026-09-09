"""Test the UniFi OS config flow."""

from collections.abc import Callable
from typing import Any

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import CONSOLE_MAC, DEFAULT_HOST, DOMAIN, USER_INPUT

pytestmark = pytest.mark.usefixtures("enable_custom_integrations", "mock_setup_entry")


async def test_user_flow(
    hass: HomeAssistant, mock_unifi_os_requests: Callable[..., None]
) -> None:
    """Test a successful user config flow."""
    mock_unifi_os_requests()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Dream Machine"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == CONSOLE_MAC


@pytest.mark.parametrize(
    ("mock_kwargs", "error"),
    [
        pytest.param({"login_status": 401}, "faulty_credentials", id="bad-creds"),
        pytest.param({"unifi_os": False}, "not_unifi_os", id="not-unifi-os"),
        pytest.param(
            {"unifi_os": True, "login_status": 503},
            "service_unavailable",
            id="unavailable",
        ),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_unifi_os_requests: Callable[..., None],
    mock_kwargs: dict[str, Any],
    error: str,
) -> None:
    """Test config flow error handling."""
    mock_unifi_os_requests(**mock_kwargs)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_unifi_os_requests: Callable[..., None],
) -> None:
    """Test the flow aborts when the console is already configured."""
    mock_config_entry.add_to_hass(hass)
    mock_unifi_os_requests()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_unifi_os_requests: Callable[..., None],
) -> None:
    """Test reauthentication updates the existing entry."""
    mock_config_entry.add_to_hass(hass)
    mock_unifi_os_requests()

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: DEFAULT_HOST,
            CONF_USERNAME: "username",
            CONF_PASSWORD: "new-password",
            CONF_PORT: 443,
            CONF_VERIFY_SSL: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_PASSWORD] == "new-password"


async def test_user_flow_recovers_from_error(
    hass: HomeAssistant,
    mock_unifi_os_requests: Callable[..., None],
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test the flow succeeds after the user corrects an error."""
    mock_unifi_os_requests(login_status=401)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["errors"] == {"base": "faulty_credentials"}

    aioclient_mock.clear_requests()
    mock_unifi_os_requests()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == CONSOLE_MAC
