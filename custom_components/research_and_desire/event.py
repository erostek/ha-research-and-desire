"""Event platform for Research and Desire."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ResearchAndDesireConfigEntry
from .const import DOMAIN, PRODUCT_DTT
from .coordinator import DttDeviceData, ResearchAndDesireCoordinator

_LOGGER = logging.getLogger(__name__)

EVENT_SESSION_PASSED = "session_passed"
EVENT_SESSION_FAILED = "session_failed"
EVENT_SESSION_COMPLETED = "session_completed"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Research and Desire event entities."""
    coordinator = entry.runtime_data
    entities = []
    data = coordinator.data
    if data:
        for device_id in data.dtt_devices:
            entities.append(ResearchAndDesireSessionEvent(coordinator, device_id))
    async_add_entities(entities)


class ResearchAndDesireSessionEvent(
    CoordinatorEntity[ResearchAndDesireCoordinator], EventEntity
):
    """Event entity that fires when a DTT session completes."""

    _attr_has_entity_name = True
    _attr_translation_key = "session_completed"
    _attr_event_types = [
        EVENT_SESSION_PASSED,
        EVENT_SESSION_FAILED,
        EVENT_SESSION_COMPLETED,
    ]

    def __init__(
        self,
        coordinator: ResearchAndDesireCoordinator,
        device_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"dtt_{device_id}_session_completed"

        device_data = coordinator.data.dtt_devices.get(device_id) if coordinator.data else None
        dev_info = device_data.device_info if device_data else {}

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"dtt_{device_id}")},
            name="Deepthroat Trainer",
            manufacturer="Research and Desire",
            model="Deepthroat Trainer",
            serial_number=dev_info.get("serialNumber"),
            sw_version=dev_info.get("softwareVersion"),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            super()._handle_coordinator_update()
            return

        device_data: DttDeviceData | None = self.coordinator.data.dtt_devices.get(self._device_id)
        if device_data is None or not device_data.new_session_completed:
            super()._handle_coordinator_update()
            return

        session = device_data.latest_session or {}
        detail = device_data.session_detail or {}
        passed = session.get("passed")

        # Compute event data from segments
        from .sensor import _get_segments
        segments = _get_segments(detail)
        total_points = sum(s.get("points", 0) for s in segments)
        grades = [s["percentGrade"] for s in segments if s.get("percentGrade") is not None]
        average_grade = round(sum(grades) / len(grades), 1) if grades else None

        event_data: dict[str, Any] = {
            "session_id": session.get("id"),
            "passed": passed,
            "total_points": total_points,
            "average_grade": average_grade,
            "segment_count": len(segments),
            "created_at": session.get("created_at") or session.get("createdAt"),
        }

        # Fire a single event -- specific type when known, generic otherwise
        if passed is True:
            self._trigger_event(EVENT_SESSION_PASSED, event_data)
        elif passed is False:
            self._trigger_event(EVENT_SESSION_FAILED, event_data)
        else:
            self._trigger_event(EVENT_SESSION_COMPLETED, event_data)

        self.async_write_ha_state()
