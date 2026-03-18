"""API client for Research and Desire cloud API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised on 401/403 responses."""


class ApiError(Exception):
    """Raised when the API returns ok: false or unexpected errors."""


def _extract_list(data: Any) -> list[dict[str, Any]]:
    """Extract a list from an API response that may be a list or paginated wrapper."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common pagination wrapper keys
        for key in ("items", "devices", "sessions", "templates", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # If the dict has numeric-looking keys or is itself a single item, wrap it
        _LOGGER.debug("Unexpected dict response, returning empty list: %s", data)
        return []
    if data is None:
        return []
    _LOGGER.warning("Unexpected response type %s: %s", type(data), data)
    return []


class ResearchAndDesireApiClient:
    """Async client for the Research and Desire API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an API request and unwrap the response envelope."""
        url = f"{API_BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as resp:
                if resp.status in (401, 403):
                    raise AuthenticationError(
                        f"Authentication failed: {resp.status}"
                    )

                data = await resp.json()
                _LOGGER.debug("API %s %s [%s] -> %s", method, path, resp.status, data)

                if resp.status >= 400:
                    error_msg = data.get("error", f"HTTP {resp.status}") if isinstance(data, dict) else f"HTTP {resp.status}"
                    raise ApiError(error_msg)

                if isinstance(data, dict) and not data.get("ok", False):
                    error_msg = data.get("error", "Unknown API error")
                    raise ApiError(error_msg)

                if isinstance(data, dict):
                    return data.get("data")
                return data

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise ApiError(f"Connection error: {err}") from err

    async def async_get_devices(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get DTT devices."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        result = await self._request("GET", "/dtt", params=params or None)
        return _extract_list(result)

    async def async_get_latest_session(self) -> dict[str, Any] | None:
        """Get the most recent DTT session (summary, no segments)."""
        try:
            result = await self._request("GET", "/dtt/sessions/latest")
            if result is None:
                return None
            # Handle if the endpoint wraps session in a key
            if isinstance(result, dict) and "session" in result:
                return result["session"]
            if isinstance(result, list) and result:
                return result[0]
            return result
        except ApiError as err:
            _LOGGER.debug("No latest session available: %s", err)
            return None

    async def async_get_session(self, session_id: int) -> dict[str, Any] | None:
        """Get a single DTT session with full segment detail."""
        try:
            result = await self._request("GET", f"/dtt/sessions/{session_id}")
            if isinstance(result, dict) and "session" in result:
                return result["session"]
            return result
        except ApiError as err:
            _LOGGER.warning("Could not fetch session %s: %s", session_id, err)
            return None

    async def async_get_active_template(self) -> dict[str, Any] | None:
        """Get the currently active DTT training template."""
        try:
            result = await self._request("GET", "/dtt/templates/active")
            if result is None:
                return None
            if isinstance(result, dict) and "template" in result:
                return result["template"]
            return result
        except ApiError as err:
            _LOGGER.debug("No active template: %s", err)
            return None

    async def async_validate_connection(self) -> bool:
        """Validate the API key by making a lightweight request."""
        await self._request("GET", "/dtt", params={"limit": 1})
        return True
