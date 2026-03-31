"""Sensor platform for Research and Desire."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
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
from .const import DOMAIN, PRODUCT_DTT, PRODUCT_LKBX, PRODUCT_OSSM
from .coordinator import (
    DttDeviceData,
    LkbxDeviceData,
    OssmDeviceData,
    ResearchAndDesireCoordinator,
    ResearchAndDesireData,
)

_SEGMENT_KEYS = (
    "TrainerSegment", "trainerSegment", "trainer_segment",
    "Segment", "segment", "Segments", "segments",
    "segment_results", "segmentResults", "results",
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ResearchAndDesireSensorDescription(SensorEntityDescription):
    """Describe a Research and Desire sensor."""

    value_fn: Callable[[Any], Any]
    attr_fn: Callable[[Any], dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string into a timezone-aware datetime."""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _get_segments(detail: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract segment list from session detail, trying all possible keys."""
    if not detail or not isinstance(detail, dict):
        return []
    for key in _SEGMENT_KEYS:
        val = detail.get(key)
        if isinstance(val, list) and val:
            return val
    for key, val in detail.items():
        if isinstance(val, list) and val and isinstance(val[0], dict) and "points" in val[0]:
            _LOGGER.debug("Found segments under unexpected key '%s'", key)
            return val
    return []


def _safe_avg(values: list[float | int | None]) -> float | None:
    """Return the average of non-None numeric values, or None."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 2)


# ---------------------------------------------------------------------------
# DTT value / attribute functions
# ---------------------------------------------------------------------------

def _dtt_session_status(d: DttDeviceData) -> str | None:
    session = d.latest_session
    if session is None:
        return None
    if session.get("passed") is True:
        return "Passed"
    if session.get("passed") is False:
        return "Failed"
    return "In Progress"


def _dtt_session_grade(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    grades = [s["percentGrade"] for s in segments if s.get("percentGrade") is not None]
    if not grades:
        return None
    return round(sum(grades) / len(grades), 1)


def _dtt_session_points(d: DttDeviceData) -> int | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return sum(s.get("points", 0) for s in segments)


def _dtt_session_date(d: DttDeviceData) -> datetime | None:
    session = d.latest_session
    if session is None:
        return None
    return _parse_datetime(session.get("created_at") or session.get("createdAt"))


def _dtt_session_segment_count(d: DttDeviceData) -> int | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return len(segments)


def _dtt_session_duration(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return sum(s.get("durationMeasured", 0) for s in segments)


def _dtt_device_software_version(d: DttDeviceData) -> str | None:
    return d.device_info.get("softwareVersion") if d.device_info else None


def _dtt_device_last_seen(d: DttDeviceData) -> datetime | None:
    return _parse_datetime(d.device_info.get("lastVisited")) if d.device_info else None


def _dtt_active_template_name(d: DttDeviceData) -> str | None:
    if d.active_template is None:
        return None
    return d.active_template.get("name")


def _dtt_target_depth(d: DttDeviceData) -> float | None:
    if d.active_template is None:
        return None
    return d.active_template.get("targetDepth")


def _dtt_session_grade_attrs(d: DttDeviceData) -> dict[str, Any]:
    segments = _get_segments(d.session_detail)
    if not segments:
        return {}
    return {
        "segment_grades": [
            {"order": s.get("order"), "grade": s.get("percentGrade"), "type": s.get("type")}
            for s in segments
        ]
    }


def _dtt_session_points_attrs(d: DttDeviceData) -> dict[str, Any]:
    segments = _get_segments(d.session_detail)
    if not segments:
        return {}
    return {
        "segment_points": [
            {"order": s.get("order"), "points": s.get("points"), "type": s.get("type")}
            for s in segments
        ]
    }


# --- New DTT helpers ---

def _dtt_template_message(d: DttDeviceData) -> str | None:
    if d.active_template is None:
        return None
    return d.active_template.get("message")


def _dtt_template_tagline(d: DttDeviceData) -> str | None:
    if d.active_template is None:
        return None
    return d.active_template.get("tagline")


def _dtt_template_toy_tagline(d: DttDeviceData) -> str | None:
    if d.active_template is None:
        return None
    return d.active_template.get("toyTagline")


def _dtt_template_hands_free_mode(d: DttDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("handsFreeMode")
    if val is None:
        return None
    return "On" if val else "Off"


def _dtt_target_window(d: DttDeviceData) -> float | None:
    if d.active_template is None:
        return None
    return d.active_template.get("targetWindow")


def _dtt_template_segment_count(d: DttDeviceData) -> int | None:
    if d.active_template is None:
        return None
    return len(d.active_template.get("Segment", []))


def _dtt_session_total_distance(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return round(sum(s.get("distanceTravelled", 0) for s in segments), 2)


def _dtt_session_longest_deepthroat(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    values = [s.get("longestDeepthroat") for s in segments if s.get("longestDeepthroat") is not None]
    if not values:
        return None
    return max(values)


def _dtt_session_total_reps(d: DttDeviceData) -> int | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return sum(s.get("repsMeasured", 0) for s in segments)


def _dtt_session_avg_stroke_length(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return _safe_avg([s.get("strokeLength") for s in segments])


def _dtt_session_avg_speed(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return _safe_avg([s.get("speedMeasured") for s in segments])


def _dtt_device_serial_number(d: DttDeviceData) -> str | None:
    return d.device_info.get("serialNumber") if d.device_info else None


def _dtt_device_last_log(d: DttDeviceData) -> datetime | None:
    return _parse_datetime(d.device_info.get("lastLogAt")) if d.device_info else None


def _dtt_active_template_attrs(d: DttDeviceData) -> dict[str, Any]:
    """Return template segment details as extra attributes."""
    if d.active_template is None:
        return {}
    template_segments = d.active_template.get("Segment", [])
    if not template_segments:
        return {}
    return {
        "template_segments": [
            {
                "order": seg.get("order"),
                "type": seg.get("type"),
                "duration": seg.get("duration"),
                "targetDepth": seg.get("targetDepth"),
                "targetWindow": seg.get("targetWindow"),
                "speed": seg.get("speed"),
                "repeat": seg.get("repeat"),
                "passGradeThreshold": seg.get("passGradeThreshold"),
                "failureText": seg.get("failureText"),
            }
            for seg in template_segments
        ]
    }


def _dtt_template_pass_threshold(d: DttDeviceData) -> float | None:
    if d.active_template is None:
        return None
    segments = d.active_template.get("Segment", [])
    thresholds = [s["passGradeThreshold"] for s in segments if s.get("passGradeThreshold") is not None and s.get("passGradeThreshold") > 0]
    if not thresholds:
        return None
    return round(sum(thresholds) / len(thresholds), 1)


def _dtt_template_total_duration(d: DttDeviceData) -> float | None:
    if d.active_template is None:
        return None
    segments = d.active_template.get("Segment", [])
    if not segments:
        return None
    return sum(s.get("duration", 0) * s.get("repeat", 1) for s in segments)


def _dtt_template_failure_text(d: DttDeviceData) -> str | None:
    if d.active_template is None:
        return None
    segments = d.active_template.get("Segment", [])
    texts = [s["failureText"] for s in segments if s.get("failureText")]
    return texts[0] if texts else None


def _dtt_template_updated_at(d: DttDeviceData) -> datetime | None:
    if d.active_template is None:
        return None
    return _parse_datetime(d.active_template.get("updatedAt"))


# --- Additional DTT session analysis ---

def _dtt_session_best_grade(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    grades = [s["percentGrade"] for s in segments if s.get("percentGrade") is not None]
    return round(max(grades), 1) if grades else None


def _dtt_session_worst_grade(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    grades = [s["percentGrade"] for s in segments if s.get("percentGrade") is not None]
    return round(min(grades), 1) if grades else None


def _dtt_session_max_speed(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    values = [s["speedMeasured"] for s in segments if s.get("speedMeasured") is not None]
    return round(max(values), 2) if values else None


def _dtt_session_passed_segments(d: DttDeviceData) -> int | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return sum(1 for s in segments if s.get("passed") is True)


def _dtt_session_failed_segments(d: DttDeviceData) -> int | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    return sum(1 for s in segments if s.get("passed") is False)


def _dtt_session_pass_rate(d: DttDeviceData) -> float | None:
    segments = _get_segments(d.session_detail)
    if not segments:
        return None
    total = len(segments)
    passed = sum(1 for s in segments if s.get("passed") is True)
    return round((passed / total) * 100, 1) if total > 0 else None


# ---------------------------------------------------------------------------
# DTT sensor descriptions
# ---------------------------------------------------------------------------

DTT_SENSOR_DESCRIPTIONS: tuple[ResearchAndDesireSensorDescription, ...] = (
    # --- Original 10 sensors (updated for DttDeviceData) ---
    ResearchAndDesireSensorDescription(
        key="session_status",
        translation_key="session_status",
        value_fn=_dtt_session_status,
    ),
    ResearchAndDesireSensorDescription(
        key="session_grade",
        translation_key="session_grade",
        native_unit_of_measurement="%",
        value_fn=_dtt_session_grade,
        attr_fn=_dtt_session_grade_attrs,
    ),
    ResearchAndDesireSensorDescription(
        key="session_points",
        translation_key="session_points",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_dtt_session_points,
        attr_fn=_dtt_session_points_attrs,
    ),
    ResearchAndDesireSensorDescription(
        key="session_date",
        translation_key="session_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_dtt_session_date,
    ),
    ResearchAndDesireSensorDescription(
        key="session_segments",
        translation_key="session_segments",
        value_fn=_dtt_session_segment_count,
    ),
    ResearchAndDesireSensorDescription(
        key="session_duration",
        translation_key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_dtt_session_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="device_software_version",
        translation_key="device_software_version",
        value_fn=_dtt_device_software_version,
    ),
    ResearchAndDesireSensorDescription(
        key="device_last_seen",
        translation_key="device_last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_dtt_device_last_seen,
    ),
    ResearchAndDesireSensorDescription(
        key="active_template",
        translation_key="active_template",
        value_fn=_dtt_active_template_name,
        attr_fn=_dtt_active_template_attrs,
    ),
    ResearchAndDesireSensorDescription(
        key="target_depth",
        translation_key="target_depth",
        native_unit_of_measurement="mm",
        value_fn=_dtt_target_depth,
    ),
    # --- New DTT sensors ---
    ResearchAndDesireSensorDescription(
        key="template_message",
        translation_key="template_message",
        value_fn=_dtt_template_message,
    ),
    ResearchAndDesireSensorDescription(
        key="template_tagline",
        translation_key="template_tagline",
        value_fn=_dtt_template_tagline,
    ),
    ResearchAndDesireSensorDescription(
        key="template_toy_tagline",
        translation_key="template_toy_tagline",
        value_fn=_dtt_template_toy_tagline,
    ),
    ResearchAndDesireSensorDescription(
        key="template_hands_free_mode",
        translation_key="template_hands_free_mode",
        value_fn=_dtt_template_hands_free_mode,
    ),
    ResearchAndDesireSensorDescription(
        key="target_window",
        translation_key="target_window",
        native_unit_of_measurement="mm",
        value_fn=_dtt_target_window,
    ),
    ResearchAndDesireSensorDescription(
        key="template_segment_count",
        translation_key="template_segment_count",
        value_fn=_dtt_template_segment_count,
    ),
    ResearchAndDesireSensorDescription(
        key="session_total_distance",
        translation_key="session_total_distance",
        native_unit_of_measurement="m",
        value_fn=_dtt_session_total_distance,
    ),
    ResearchAndDesireSensorDescription(
        key="session_longest_deepthroat",
        translation_key="session_longest_deepthroat",
        native_unit_of_measurement="ms",
        value_fn=_dtt_session_longest_deepthroat,
    ),
    ResearchAndDesireSensorDescription(
        key="session_total_reps",
        translation_key="session_total_reps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_dtt_session_total_reps,
    ),
    ResearchAndDesireSensorDescription(
        key="session_avg_stroke_length",
        translation_key="session_avg_stroke_length",
        native_unit_of_measurement="mm",
        value_fn=_dtt_session_avg_stroke_length,
    ),
    ResearchAndDesireSensorDescription(
        key="session_avg_speed",
        translation_key="session_avg_speed",
        value_fn=_dtt_session_avg_speed,
    ),
    ResearchAndDesireSensorDescription(
        key="device_serial_number",
        translation_key="device_serial_number",
        value_fn=_dtt_device_serial_number,
    ),
    ResearchAndDesireSensorDescription(
        key="device_last_log",
        translation_key="device_last_log",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_dtt_device_last_log,
    ),
    ResearchAndDesireSensorDescription(
        key="session_best_grade",
        translation_key="session_best_grade",
        native_unit_of_measurement="%",
        value_fn=_dtt_session_best_grade,
    ),
    ResearchAndDesireSensorDescription(
        key="session_worst_grade",
        translation_key="session_worst_grade",
        native_unit_of_measurement="%",
        value_fn=_dtt_session_worst_grade,
    ),
    ResearchAndDesireSensorDescription(
        key="session_max_speed",
        translation_key="session_max_speed",
        value_fn=_dtt_session_max_speed,
    ),
    ResearchAndDesireSensorDescription(
        key="session_passed_segments",
        translation_key="session_passed_segments",
        value_fn=_dtt_session_passed_segments,
    ),
    ResearchAndDesireSensorDescription(
        key="session_failed_segments",
        translation_key="session_failed_segments",
        value_fn=_dtt_session_failed_segments,
    ),
    ResearchAndDesireSensorDescription(
        key="session_pass_rate",
        translation_key="session_pass_rate",
        native_unit_of_measurement="%",
        value_fn=_dtt_session_pass_rate,
    ),
    ResearchAndDesireSensorDescription(
        key="template_pass_threshold",
        translation_key="template_pass_threshold",
        native_unit_of_measurement="%",
        value_fn=_dtt_template_pass_threshold,
    ),
    ResearchAndDesireSensorDescription(
        key="template_total_duration",
        translation_key="template_total_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_dtt_template_total_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="template_failure_text",
        translation_key="template_failure_text",
        value_fn=_dtt_template_failure_text,
    ),
    ResearchAndDesireSensorDescription(
        key="template_updated_at",
        translation_key="template_updated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_dtt_template_updated_at,
    ),
)


# ---------------------------------------------------------------------------
# OSSM value functions
# ---------------------------------------------------------------------------

def _ossm_session_count(d: OssmDeviceData) -> int:
    return len(d.sessions) if d.sessions else 0


def _ossm_pattern_count(d: OssmDeviceData) -> int:
    return len(d.patterns) if d.patterns else 0


def _ossm_firmware_version(d: OssmDeviceData) -> str | None:
    if not d.firmware:
        return None
    if isinstance(d.firmware, dict):
        return d.firmware.get("version") or d.firmware.get("firmwareVersion")
    return str(d.firmware)


def _ossm_device_last_seen(d: OssmDeviceData) -> datetime | None:
    return _parse_datetime(d.device_info.get("lastVisited")) if d.device_info else None


# ---------------------------------------------------------------------------
# OSSM sensor descriptions
# ---------------------------------------------------------------------------

OSSM_SENSOR_DESCRIPTIONS: tuple[ResearchAndDesireSensorDescription, ...] = (
    ResearchAndDesireSensorDescription(
        key="ossm_session_count",
        translation_key="ossm_session_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_ossm_session_count,
    ),
    ResearchAndDesireSensorDescription(
        key="ossm_pattern_count",
        translation_key="ossm_pattern_count",
        value_fn=_ossm_pattern_count,
    ),
    ResearchAndDesireSensorDescription(
        key="ossm_firmware_version",
        translation_key="ossm_firmware_version",
        value_fn=_ossm_firmware_version,
    ),
    ResearchAndDesireSensorDescription(
        key="ossm_device_last_seen",
        translation_key="ossm_device_last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_ossm_device_last_seen,
    ),
)


# ---------------------------------------------------------------------------
# LKBX value functions
# ---------------------------------------------------------------------------

def _lkbx_locked(d: LkbxDeviceData) -> str | None:
    if d.device_info is None:
        return None
    # Active template is the most reliable indicator of lock state
    if d.active_template is not None:
        return "Locked"
    locked = d.device_info.get("locked")
    if locked is None:
        return None
    return "Locked" if locked else "Unlocked"


def _lkbx_last_seen(d: LkbxDeviceData) -> datetime | None:
    return _parse_datetime(d.device_info.get("lastVisited")) if d.device_info else None


def _lkbx_mac_address(d: LkbxDeviceData) -> str | None:
    return d.device_info.get("macAddress") if d.device_info else None


def _lkbx_active_lock(d: LkbxDeviceData) -> str:
    if d.active_template and d.active_template.get("name"):
        return d.active_template["name"]
    return "No active lock"


def _lkbx_lock_duration(d: LkbxDeviceData) -> int | None:
    if d.active_template is None:
        return None
    return d.active_template.get("duration")


def _lkbx_break_enabled(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isBreakEnabled")
    if val is None:
        return None
    return "On" if val else "Off"


def _lkbx_emergency_unlock(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isEmergencyUnlockEnabled")
    if val is None:
        return None
    return "On" if val else "Off"


def _lkbx_deepthroat_enabled(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isDeepthroatEnabled")
    if val is None:
        return None
    return "On" if val else "Off"


def _lkbx_shame_enabled(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isShameEnabled")
    if val is None:
        return None
    return "On" if val else "Off"


def _lkbx_test_lock(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isTestLock")
    if val is None:
        return None
    return "Yes" if val else "No"


def _lkbx_break_regularity(d: LkbxDeviceData) -> float | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("breakRegularity")
    return val if val is not None else None


def _lkbx_break_penalty(d: LkbxDeviceData) -> float | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("breakPenalty")
    return val if val is not None else None


def _lkbx_break_maximum(d: LkbxDeviceData) -> float | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("breakMaximum")
    return val if val is not None else None


def _lkbx_dtt_time_reduction(d: LkbxDeviceData) -> float | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("deepthroatTimeReduction")
    return val if val is not None else None


def _lkbx_min_duration(d: LkbxDeviceData) -> int | None:
    if d.active_template is None:
        return None
    return d.active_template.get("minDuration")


def _lkbx_max_duration(d: LkbxDeviceData) -> int | None:
    if d.active_template is None:
        return None
    return d.active_template.get("maxDuration")


def _lkbx_random_duration(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isRandomDuration")
    if val is None:
        return None
    return "On" if val else "Off"


def _lkbx_time_displayed(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isTimeDisplayed")
    if val is None:
        return None
    return "Yes" if val else "No"


def _lkbx_publicly_listed(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("isPubliclyListed")
    if val is None:
        return None
    return "Yes" if val else "No"


def _lkbx_shame_time_add(d: LkbxDeviceData) -> int | None:
    if d.active_template is None:
        return None
    return d.active_template.get("shameTimeAdd")


def _lkbx_break_keyholder_only(d: LkbxDeviceData) -> str | None:
    if d.active_template is None:
        return None
    val = d.active_template.get("breakKeyholderOnly")
    if val is None:
        return None
    return "Yes" if val else "No"


def _lkbx_template_count(d: LkbxDeviceData) -> int:
    return len(d.templates) if d.templates else 0


def _lkbx_session_count(d: LkbxDeviceData) -> int:
    return len(d.sessions) if d.sessions else 0


def _lkbx_active_lock_attrs(d: LkbxDeviceData) -> dict[str, Any]:
    """Return active lock template details as extra attributes."""
    if d.active_template is None:
        return {}
    return {
        "duration": d.active_template.get("duration"),
        "is_random_duration": d.active_template.get("isRandomDuration"),
        "min_duration": d.active_template.get("minDuration"),
        "max_duration": d.active_template.get("maxDuration"),
        "break_regularity": d.active_template.get("breakRegularity"),
        "break_maximum": d.active_template.get("breakMaximum"),
        "break_penalty": d.active_template.get("breakPenalty"),
        "is_time_displayed": d.active_template.get("isTimeDisplayed"),
    }


# ---------------------------------------------------------------------------
# LKBX sensor descriptions
# ---------------------------------------------------------------------------

LKBX_SENSOR_DESCRIPTIONS: tuple[ResearchAndDesireSensorDescription, ...] = (
    ResearchAndDesireSensorDescription(
        key="lkbx_locked",
        translation_key="lkbx_locked",
        value_fn=_lkbx_locked,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_last_seen",
        translation_key="lkbx_last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_lkbx_last_seen,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_mac_address",
        translation_key="lkbx_mac_address",
        value_fn=_lkbx_mac_address,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_active_lock",
        translation_key="lkbx_active_lock",
        value_fn=_lkbx_active_lock,
        attr_fn=_lkbx_active_lock_attrs,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_lock_duration",
        translation_key="lkbx_lock_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_lock_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_break_enabled",
        translation_key="lkbx_break_enabled",
        value_fn=_lkbx_break_enabled,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_emergency_unlock",
        translation_key="lkbx_emergency_unlock",
        value_fn=_lkbx_emergency_unlock,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_deepthroat_enabled",
        translation_key="lkbx_deepthroat_enabled",
        value_fn=_lkbx_deepthroat_enabled,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_shame_enabled",
        translation_key="lkbx_shame_enabled",
        value_fn=_lkbx_shame_enabled,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_test_lock",
        translation_key="lkbx_test_lock",
        value_fn=_lkbx_test_lock,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_break_regularity",
        translation_key="lkbx_break_regularity",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_break_regularity,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_break_penalty",
        translation_key="lkbx_break_penalty",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_break_penalty,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_break_maximum",
        translation_key="lkbx_break_maximum",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_break_maximum,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_dtt_time_reduction",
        translation_key="lkbx_dtt_time_reduction",
        value_fn=_lkbx_dtt_time_reduction,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_min_duration",
        translation_key="lkbx_min_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_min_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_max_duration",
        translation_key="lkbx_max_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_max_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_random_duration",
        translation_key="lkbx_random_duration",
        value_fn=_lkbx_random_duration,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_time_displayed",
        translation_key="lkbx_time_displayed",
        value_fn=_lkbx_time_displayed,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_publicly_listed",
        translation_key="lkbx_publicly_listed",
        value_fn=_lkbx_publicly_listed,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_template_count",
        translation_key="lkbx_template_count",
        value_fn=_lkbx_template_count,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_session_count",
        translation_key="lkbx_session_count",
        value_fn=_lkbx_session_count,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_shame_time_add",
        translation_key="lkbx_shame_time_add",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        value_fn=_lkbx_shame_time_add,
    ),
    ResearchAndDesireSensorDescription(
        key="lkbx_break_keyholder_only",
        translation_key="lkbx_break_keyholder_only",
        value_fn=_lkbx_break_keyholder_only,
    ),
)


# ---------------------------------------------------------------------------
# Device info builder
# ---------------------------------------------------------------------------

_PRODUCT_MODELS = {
    PRODUCT_DTT: "Deepthroat Trainer",
    PRODUCT_OSSM: "OSSM",
    PRODUCT_LKBX: "Lockbox",
}


def _build_device_info(
    product_type: str,
    device_id: int,
    data: ResearchAndDesireData,
) -> DeviceInfo:
    """Build HA DeviceInfo for a specific product device."""
    model = _PRODUCT_MODELS.get(product_type, "Unknown")

    dev_data: DttDeviceData | OssmDeviceData | LkbxDeviceData | None = None
    if product_type == PRODUCT_DTT:
        dev_data = data.dtt_devices.get(device_id)
    elif product_type == PRODUCT_OSSM:
        dev_data = data.ossm_devices.get(device_id)
    elif product_type == PRODUCT_LKBX:
        dev_data = data.lkbx_devices.get(device_id)

    device_info_dict: dict[str, Any] = dev_data.device_info if dev_data and dev_data.device_info else {}
    sw = device_info_dict.get("softwareVersion")

    return DeviceInfo(
        identifiers={(DOMAIN, f"{product_type}_{device_id}")},
        name=model,
        manufacturer="Research and Desire",
        model=model,
        sw_version=sw if sw and sw != "undefined" else None,
    )


# ---------------------------------------------------------------------------
# Entity setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Research and Desire sensors."""
    coordinator: ResearchAndDesireCoordinator = entry.runtime_data
    entities: list[ResearchAndDesireSensor] = []

    data = coordinator.data
    if data:
        for device_id in data.dtt_devices:
            for desc in DTT_SENSOR_DESCRIPTIONS:
                entities.append(
                    ResearchAndDesireSensor(coordinator, desc, device_id, PRODUCT_DTT)
                )
        for device_id in data.ossm_devices:
            for desc in OSSM_SENSOR_DESCRIPTIONS:
                entities.append(
                    ResearchAndDesireSensor(coordinator, desc, device_id, PRODUCT_OSSM)
                )
        for device_id in data.lkbx_devices:
            for desc in LKBX_SENSOR_DESCRIPTIONS:
                entities.append(
                    ResearchAndDesireSensor(coordinator, desc, device_id, PRODUCT_LKBX)
                )

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Sensor entity
# ---------------------------------------------------------------------------

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
        device_id: int,
        product_type: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._product_type = product_type
        self._attr_unique_id = f"{product_type}_{device_id}_{description.key}"
        self._attr_device_info = _build_device_info(
            product_type, device_id, coordinator.data
        )

    def _get_device_data(self) -> DttDeviceData | OssmDeviceData | LkbxDeviceData | None:
        """Resolve the device-specific data object from coordinator data."""
        data = self.coordinator.data
        if data is None:
            return None
        if self._product_type == PRODUCT_DTT:
            return data.dtt_devices.get(self._device_id)
        if self._product_type == PRODUCT_OSSM:
            return data.ossm_devices.get(self._device_id)
        if self._product_type == PRODUCT_LKBX:
            return data.lkbx_devices.get(self._device_id)
        return None

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        device_data = self._get_device_data()
        if device_data is None:
            return None
        return self.entity_description.value_fn(device_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn is None:
            return None
        device_data = self._get_device_data()
        if device_data is None:
            return None
        return self.entity_description.attr_fn(device_data)
