"""UniFi OS login and GET /api/system."""

import asyncio
import ssl
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Literal

import aiounifi
from aiohttp import ClientError, CookieJar
from aiounifi.models.configuration import Configuration
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import LOGGER
from .errors import AuthenticationRequired, CannotConnect, NotUnifiOs


async def async_get_controller(
    hass: HomeAssistant,
    config: Mapping[str, Any],
) -> aiounifi.Controller:
    """Create an aiounifi controller and log in."""
    ssl_context: ssl.SSLContext | Literal[False] = False

    if verify_ssl := config.get(CONF_VERIFY_SSL):
        session = aiohttp_client.async_get_clientsession(hass)
        if isinstance(verify_ssl, str):
            ssl_context = ssl.create_default_context(cafile=verify_ssl)
    else:
        session = aiohttp_client.async_create_clientsession(
            hass, verify_ssl=False, cookie_jar=CookieJar(unsafe=True)
        )

    api = aiounifi.Controller(
        Configuration(
            session,
            host=config[CONF_HOST],
            username=config[CONF_USERNAME],
            password=config[CONF_PASSWORD],
            port=config[CONF_PORT],
            site="default",
            ssl_context=ssl_context,
        )
    )

    try:
        async with asyncio.timeout(10):
            await api.login()
    except aiounifi.Unauthorized as err:
        raise AuthenticationRequired from err
    except (
        TimeoutError,
        aiounifi.BadGateway,
        aiounifi.Forbidden,
        aiounifi.ServiceUnavailable,
        aiounifi.RequestError,
        aiounifi.ResponseError,
    ) as err:
        LOGGER.debug("Error connecting to UniFi OS at %s: %s", config[CONF_HOST], err)
        raise CannotConnect from err
    except aiounifi.LoginRequired as err:
        raise AuthenticationRequired from err
    except aiounifi.AiounifiException as err:
        LOGGER.exception("Unknown UniFi OS communication error: %s", err)
        raise AuthenticationRequired from err

    if not api.connectivity.is_unifi_os:
        raise NotUnifiOs

    return api


async def async_get_system(api: aiounifi.Controller) -> dict[str, Any]:
    """Fetch GET /api/system using the authenticated aiounifi session."""
    try:
        return await _request_system(api)
    except AuthenticationRequired:
        await api.login()
        return await _request_system(api)


async def _request_system(api: aiounifi.Controller) -> dict[str, Any]:
    """Perform GET /api/system once."""
    url = f"{api.connectivity.config.url}/api/system"
    try:
        async with api.connectivity.config.session.get(
            url,
            ssl=api.connectivity.config.ssl_context,
            headers=api.connectivity.headers,
        ) as response:
            if response.status == HTTPStatus.UNAUTHORIZED:
                raise AuthenticationRequired
            if response.status >= HTTPStatus.BAD_REQUEST:
                raise CannotConnect
            return await response.json()
    except (TimeoutError, OSError, ClientError) as err:
        raise CannotConnect from err
