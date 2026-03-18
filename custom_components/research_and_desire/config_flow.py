"""Config flow for Research and Desire integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthenticationError, ApiError, ResearchAndDesireApiClient
from .const import CONF_API_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class ResearchAndDesireConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Research and Desire."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = ResearchAndDesireApiClient(session, user_input[CONF_API_KEY])

            try:
                result = await client.async_get_devices(limit=1)
                _LOGGER.debug("API /dtt response: %s (type: %s)", result, type(result))

                # Handle both list and paginated wrapper responses
                if isinstance(result, list):
                    devices = result
                elif isinstance(result, dict):
                    # Paginated: data might be under a key like "items" or "devices"
                    for key in ("items", "devices", "data"):
                        if key in result and isinstance(result[key], list):
                            devices = result[key]
                            break
                    else:
                        devices = []
                else:
                    devices = []

            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (ApiError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during setup")
                errors["base"] = "unknown"
            else:
                # Use first device's bubbleId as unique ID to prevent duplicates
                if devices and isinstance(devices[0], dict):
                    bubble_id = devices[0].get("bubbleId")
                    if bubble_id:
                        await self.async_set_unique_id(str(bubble_id))
                        self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Research and Desire",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
