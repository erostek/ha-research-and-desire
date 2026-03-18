"""DataUpdateCoordinator for Research and Desire."""

from __future__ import annotations

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
        """Fetch data from the API sequentially."""
        prev = self.data

        # Fetch endpoints sequentially to avoid API rate issues
        try:
            latest_session = await self.client.async_get_latest_session()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            _LOGGER.warning("Failed to fetch latest session: %s", err)
            latest_session = prev.latest_session if prev else None

        try:
            devices = await self.client.async_get_devices()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            _LOGGER.warning("Failed to fetch devices: %s", err)
            devices = prev.devices if prev else []

        try:
            active_template = await self.client.async_get_active_template()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            _LOGGER.warning("Failed to fetch active template: %s", err)
            active_template = prev.active_template if prev else None

        _LOGGER.debug(
            "Poll: session=%s, devices=%d, template=%s",
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
                self._first_poll = False
                self._last_session_id = current_session_id
                session_detail = await self._fetch_session_detail(current_session_id)
            elif current_session_id != self._last_session_id:
                self._last_session_id = current_session_id
                new_session_completed = True
                session_detail = await self._fetch_session_detail(current_session_id)
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

    async def _fetch_session_detail(self, session_id: int) -> dict[str, Any] | None:
        """Fetch session detail with error handling."""
        try:
            detail = await self.client.async_get_session(session_id)
            if detail:
                _LOGGER.debug("Session detail keys: %s", list(detail.keys()) if isinstance(detail, dict) else type(detail))
            else:
                _LOGGER.warning("Session detail for %s returned empty", session_id)
            return detail
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            _LOGGER.warning("Could not fetch session detail %s: %s", session_id, err)
            return None
