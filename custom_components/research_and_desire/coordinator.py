"""DataUpdateCoordinator for Research and Desire."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthenticationError, ResearchAndDesireApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class ResearchAndDesireData:
    """Data returned by the coordinator."""

    latest_session: dict[str, Any] | None = None
    session_detail: dict[str, Any] | None = None
    devices: list[dict[str, Any]] = field(default_factory=list)
    active_template: dict[str, Any] | None = None
    new_session_completed: bool = False


class ResearchAndDesireCoordinator(DataUpdateCoordinator[ResearchAndDesireData]):
    """Coordinator that polls the Research and Desire API."""

    def __init__(self, hass: HomeAssistant, client: ResearchAndDesireApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._last_session_id: int | None = None
        self._first_poll = True

    async def _async_update_data(self) -> ResearchAndDesireData:
        """Fetch data from the API."""
        # Fetch all endpoints in parallel, isolating failures
        results = await asyncio.gather(
            self.client.async_get_latest_session(),
            self.client.async_get_devices(),
            self.client.async_get_active_template(),
            return_exceptions=True,
        )

        # Check for auth failures first
        for result in results:
            if isinstance(result, AuthenticationError):
                raise ConfigEntryAuthFailed(str(result)) from result

        # Unpack results, falling back to previous data or defaults on failure
        prev = self.data

        if isinstance(results[0], BaseException):
            _LOGGER.warning("Failed to fetch latest session: %s", results[0])
            latest_session = prev.latest_session if prev else None
        else:
            latest_session = results[0]

        if isinstance(results[1], BaseException):
            _LOGGER.warning("Failed to fetch devices: %s", results[1])
            devices = prev.devices if prev else []
        else:
            devices = results[1] if isinstance(results[1], list) else []

        if isinstance(results[2], BaseException):
            _LOGGER.warning("Failed to fetch active template: %s", results[2])
            active_template = prev.active_template if prev else None
        else:
            active_template = results[2]

        # If ALL three failed (not auth), raise UpdateFailed
        all_failed = all(isinstance(r, BaseException) for r in results)
        if all_failed:
            raise UpdateFailed("All API endpoints failed")

        _LOGGER.debug(
            "Poll result: session=%s, devices=%d, template=%s",
            latest_session.get("id") if isinstance(latest_session, dict) else None,
            len(devices),
            active_template.get("name") if isinstance(active_template, dict) else None,
        )

        # Detect new session completion
        new_session_completed = False
        session_detail = None
        current_session_id = None

        if isinstance(latest_session, dict):
            current_session_id = latest_session.get("id")

        if current_session_id is not None:
            if self._first_poll:
                # First poll — record ID, fetch detail, but don't fire event
                self._first_poll = False
                self._last_session_id = current_session_id
                session_detail = await self.client.async_get_session(current_session_id)
            elif current_session_id != self._last_session_id:
                # New session detected
                self._last_session_id = current_session_id
                new_session_completed = True
                session_detail = await self.client.async_get_session(current_session_id)
            else:
                # Same session — reuse previous detail
                if prev and prev.session_detail:
                    session_detail = prev.session_detail
        else:
            self._first_poll = False

        return ResearchAndDesireData(
            latest_session=latest_session,
            session_detail=session_detail,
            devices=devices,
            active_template=active_template,
            new_session_completed=new_session_completed,
        )
