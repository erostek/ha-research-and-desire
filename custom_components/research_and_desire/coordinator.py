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
class DttDeviceData:
    """Data for a single DTT device."""

    device_info: dict[str, Any]
    latest_session: dict[str, Any] | None = None
    session_detail: dict[str, Any] | None = None
    active_template: dict[str, Any] | None = None
    new_session_completed: bool = False


@dataclass
class OssmDeviceData:
    """Data for a single OSSM device."""

    device_info: dict[str, Any]
    sessions: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    settings: dict[str, Any] | None = None
    firmware: dict[str, Any] | None = None


@dataclass
class LkbxDeviceData:
    """Data for a single Lockbox device."""

    device_info: dict[str, Any]  # has: id, bubbleId, macAddress, locked, hueShift, lastVisited
    sessions: list[dict[str, Any]] = field(default_factory=list)
    latest_session: dict[str, Any] | None = None
    templates: list[dict[str, Any]] = field(default_factory=list)
    active_template: dict[str, Any] | None = None


@dataclass
class ResearchAndDesireData:
    """All data returned by the coordinator."""

    dtt_devices: dict[int, DttDeviceData] = field(default_factory=dict)
    ossm_devices: dict[int, OssmDeviceData] = field(default_factory=dict)
    lkbx_devices: dict[int, LkbxDeviceData] = field(default_factory=dict)


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
        try:
            return await self._do_update()
        except (ConfigEntryAuthFailed, UpdateFailed):
            raise
        except Exception as err:
            # Catch unexpected errors to prevent the coordinator from dying
            _LOGGER.error("Unexpected error during update: %s", err, exc_info=True)
            if self.data:
                return self.data
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _safe_fetch(self, coro, fallback=None):
        """Execute an API coroutine with standard error handling."""
        try:
            result = await coro
            return result
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            _LOGGER.warning("API call failed: %s", err)
            return fallback

    async def _do_update(self) -> ResearchAndDesireData:
        """Perform the actual data update."""
        prev = self.data

        # ------------------------------------------------------------------
        # DTT devices
        # ------------------------------------------------------------------
        raw_dtt_devices = await self._safe_fetch(
            self.client.async_get_dtt_devices(),
            fallback=prev.dtt_devices if prev else {},
        )

        # Normalise: API returns a list; build a dict keyed by device id
        dtt_device_list: list[dict[str, Any]] = (
            raw_dtt_devices if isinstance(raw_dtt_devices, list) else []
        )
        dtt_devices: dict[int, DttDeviceData] = {}
        for dev in dtt_device_list:
            dev_id = dev.get("id")
            if dev_id is not None:
                dtt_devices[dev_id] = DttDeviceData(device_info=dev)

        # Fetch latest session (global endpoint)
        latest_session = await self._safe_fetch(
            self.client.async_get_dtt_sessions_latest(),
            fallback=None,
        )

        # Fetch active template (global endpoint)
        active_template = await self._safe_fetch(
            self.client.async_get_dtt_templates_active(),
            fallback=None,
        )

        _LOGGER.debug(
            "Poll: dtt_devices=%d, session=%s, template=%s",
            len(dtt_devices),
            latest_session.get("id") if isinstance(latest_session, dict) else None,
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
                # Same session - reuse previous detail
                if prev:
                    # Find previous detail from the matching DTT device
                    for prev_dtt in prev.dtt_devices.values():
                        if prev_dtt.session_detail:
                            session_detail = prev_dtt.session_detail
                            break
        else:
            self._first_poll = False

        # Assign session data to the matching DTT device by trainer_id
        trainer_id = (
            latest_session.get("trainer_id")
            if isinstance(latest_session, dict)
            else None
        )
        if trainer_id is not None and trainer_id in dtt_devices:
            dtt_devices[trainer_id].latest_session = latest_session
            dtt_devices[trainer_id].session_detail = session_detail
            dtt_devices[trainer_id].active_template = active_template
            dtt_devices[trainer_id].new_session_completed = new_session_completed
        elif dtt_devices:
            # Fallback: assign to the first device if trainer_id doesn't match
            first_id = next(iter(dtt_devices))
            dtt_devices[first_id].latest_session = latest_session
            dtt_devices[first_id].session_detail = session_detail
            dtt_devices[first_id].active_template = active_template
            dtt_devices[first_id].new_session_completed = new_session_completed

        # ------------------------------------------------------------------
        # OSSM devices
        # ------------------------------------------------------------------
        raw_ossm_devices = await self._safe_fetch(
            self.client.async_get_ossm_devices(),
            fallback=[],
        )
        ossm_device_list: list[dict[str, Any]] = (
            raw_ossm_devices if isinstance(raw_ossm_devices, list) else []
        )
        ossm_devices: dict[int, OssmDeviceData] = {}
        for dev in ossm_device_list:
            dev_id = dev.get("id")
            if dev_id is not None:
                ossm_devices[dev_id] = OssmDeviceData(device_info=dev)

        if ossm_devices:
            ossm_sessions = await self._safe_fetch(
                self.client.async_get_ossm_sessions(), fallback=[]
            )
            ossm_patterns = await self._safe_fetch(
                self.client.async_get_ossm_patterns(), fallback=[]
            )
            ossm_settings = await self._safe_fetch(
                self.client.async_get_ossm_settings(), fallback=None
            )
            ossm_firmware = await self._safe_fetch(
                self.client.async_get_ossm_firmware(), fallback=None
            )

            # Distribute sessions/patterns to devices if possible;
            # otherwise assign all to every device (API may not have per-device filtering)
            for dev_id, dev_data in ossm_devices.items():
                dev_data.sessions = (
                    ossm_sessions if isinstance(ossm_sessions, list) else []
                )
                dev_data.patterns = (
                    ossm_patterns if isinstance(ossm_patterns, list) else []
                )
                dev_data.settings = ossm_settings
                dev_data.firmware = ossm_firmware

        # ------------------------------------------------------------------
        # LKBX devices
        # ------------------------------------------------------------------
        raw_lkbx_devices = await self._safe_fetch(
            self.client.async_get_lkbx_devices(),
            fallback=[],
        )
        lkbx_device_list: list[dict[str, Any]] = (
            raw_lkbx_devices if isinstance(raw_lkbx_devices, list) else []
        )
        lkbx_devices: dict[int, LkbxDeviceData] = {}
        for dev in lkbx_device_list:
            dev_id = dev.get("id")
            if dev_id is not None:
                lkbx_devices[dev_id] = LkbxDeviceData(device_info=dev)

        if lkbx_devices:
            lkbx_sessions = await self._safe_fetch(
                self.client.async_get_lkbx_sessions(), fallback=[]
            )
            lkbx_latest_session = await self._safe_fetch(
                self.client.async_get_lkbx_sessions_latest(), fallback=None
            )
            lkbx_templates = await self._safe_fetch(
                self.client.async_get_lkbx_templates(), fallback=[]
            )
            lkbx_active_template = await self._safe_fetch(
                self.client.async_get_lkbx_templates_active(), fallback=None
            )

            for dev_id, dev_data in lkbx_devices.items():
                dev_data.sessions = (
                    lkbx_sessions if isinstance(lkbx_sessions, list) else []
                )
                dev_data.latest_session = lkbx_latest_session
                dev_data.templates = (
                    lkbx_templates if isinstance(lkbx_templates, list) else []
                )
                dev_data.active_template = lkbx_active_template

        # ------------------------------------------------------------------
        # Build final result
        # ------------------------------------------------------------------
        return ResearchAndDesireData(
            dtt_devices=dtt_devices,
            ossm_devices=ossm_devices,
            lkbx_devices=lkbx_devices,
        )

    async def _fetch_session_detail(self, session_id: int) -> dict[str, Any] | None:
        """Fetch session detail with error handling."""
        try:
            detail = await self.client.async_get_dtt_session(session_id)
            if detail:
                _LOGGER.debug(
                    "Session detail keys: %s",
                    list(detail.keys()) if isinstance(detail, dict) else type(detail),
                )
            else:
                _LOGGER.warning("Session detail for %s returned empty", session_id)
            return detail
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            _LOGGER.warning("Could not fetch session detail %s: %s", session_id, err)
            return None
