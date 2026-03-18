"""Sensor platform for Research and Desire."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ResearchAndDesireConfigEntry
from .const import DOMAIN
from .coordinator import ResearchAndDesireCoordinator, ResearchAndDesireData


@dataclass(frozen=True, kw_only=True)
class ResearchAndDesireSensorDescription(SensorEntityDescription):
    """Describe a Research and Desire sensor."""

    value_fn: Callable[[ResearchAndDesireData], Any]
    attr_fn: Callable[[ResearchAndDesireData], dict[str, Any]] | None = None


def _session_status(data: ResearchAndDesireData) -> str | None:
    session = data.latest_session
    if session is None:
        return None
    if session.get("passed") is True:
        return "Passed"
    if session.get("passed") is False:
        return "Failed"
    return "In Progress"


def _session_grade(data: ResearchAndDesireData) -> float | None:
    detail = data.session_detail
    if not detail:
        return None
    segments = detail.get("TrainerSegment") or detail.get("trainerSegment") or []
    if not segments:
        return None
    grades = [s["percentGrade"] for s in segments if s.get("percentGrade") is not None]
    if not grades:
        return None
    return round(sum(grades) / len(grades), 1)


def _session_points(data: ResearchAndDesireData) -> int | None:
    detail = data.session_detail
    if not detail:
        return None
    segments = detail.get("TrainerSegment") or detail.get("trainerSegment") or []
    if not segments:
        return None
    return sum(s.get("points", 0) for s in segments)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string into a timezone-aware datetime."""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
        # HA TIMESTAMP sensors require timezone-aware datetimes
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _session_date(data: ResearchAndDesireData) -> datetime | None:
    session = data.latest_session
    if session is None:
        return None
    return _parse_datetime(session.get("created_at") or session.get("createdAt"))


def _session_segment_count(data: ResearchAndDesireData) -> int | None:
    detail = data.session_detail
    if not detail:
        return None
    segments = detail.get("TrainerSegment") or detail.get("trainerSegment") or []
    return len(segments)


def _session_duration(data: ResearchAndDesireData) -> float | None:
    detail = data.session_detail
    if not detail:
        return None
    segments = detail.get("TrainerSegment") or detail.get("trainerSegment") or []
    if not segments:
        return None
    return sum(s.get("durationMeasured", 0) for s in segments)


def _device_software_version(data: ResearchAndDesireData) -> str | None:
    if not data.devices:
        return None
    return data.devices[0].get("softwareVersion")


def _device_last_seen(data: ResearchAndDesireData) -> datetime | None:
    if not data.devices:
        return None
    return _parse_datetime(data.devices[0].get("lastVisited"))


def _active_template_name(data: ResearchAndDesireData) -> str | None:
    if data.active_template is None:
        return None
    return data.active_template.get("name")


def _target_depth(data: ResearchAndDesireData) -> float | None:
    if data.active_template is None:
        return None
    return data.active_template.get("targetDepth")


def _session_grade_attrs(data: ResearchAndDesireData) -> dict[str, Any]:
    detail = data.session_detail
    if not detail:
        return {}
    segments = detail.get("TrainerSegment") or detail.get("trainerSegment") or []
    return {
        "segment_grades": [
            {"order": s.get("order"), "grade": s.get("percentGrade"), "type": s.get("type")}
            for s in segments
        ]
    }


def _session_points_attrs(data: ResearchAndDesireData) -> dict[str, Any]:
    detail = data.session_detail
    if not detail:
        return {}
    segments = detail.get("TrainerSegment") or detail.get("trainerSegment") or []
    return {
        "segment_points": [
            {"order": s.get("order"), "points": s.get("points"), "type": s.get("type")}
            for s in segments
        ]
    }


SENSOR_DESCRIPTIONS: tuple[ResearchAndDesireSensorDescription, ...] = (
    ResearchAndDesireSensorDescription(
        key="session_status",
        translation_key="session_status",
        value_fn=_session_status,
    ),
    ResearchAndDesireSensorDescription(
        key="session_grade",
        translation_key="session_grade",
        native_unit_of_measurement="%",
        value_fn=_session_grade,
        attr_fn=_session_grade_attrs,
    ),
    ResearchAndDesireSensorDescription(
        key="session_points",
        translation_key="session_points",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_session_points,
        attr_fn=_session_points_attrs,
    ),
    ResearchAndDesireSensorDescription(
        key="session_date",
        translation_key="session_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_session_date,
    ),
    ResearchAndDesireSensorDescription(
        key="session_segments",
        translation_key="session_segments",
        value_fn=_session_segment_count,
    ),
    ResearchAndDesireSensorDescription(
        key="session_duration",
        translation_key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_session_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="device_software_version",
        translation_key="device_software_version",
        value_fn=_device_software_version,
    ),
    ResearchAndDesireSensorDescription(
        key="device_last_seen",
        translation_key="device_last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_device_last_seen,
    ),
    ResearchAndDesireSensorDescription(
        key="active_template",
        translation_key="active_template",
        value_fn=_active_template_name,
    ),
    ResearchAndDesireSensorDescription(
        key="target_depth",
        translation_key="target_depth",
        native_unit_of_measurement="mm",
        value_fn=_target_depth,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Research and Desire sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        ResearchAndDesireSensor(coordinator, description, entry.entry_id)
        for description in SENSOR_DESCRIPTIONS
    )


class ResearchAndDesireSensor(
    CoordinatorEntity[ResearchAndDesireCoordinator], SensorEntity
):
    """Representation of a Research and Desire sensor."""

    entity_description: ResearchAndDesireSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ResearchAndDesireCoordinator,
        description: ResearchAndDesireSensorDescription,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="DTT Trainer",
            manufacturer="Research and Desire",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None or self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
