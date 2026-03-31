"""Number platform for Research and Desire."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ResearchAndDesireConfigEntry
from .api import ApiError
from .const import DOMAIN
from .coordinator import (
    DttDeviceData,
    LkbxDeviceData,
    ResearchAndDesireCoordinator,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator: ResearchAndDesireCoordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    data = coordinator.data
    if data:
        for device_id in data.dtt_devices:
            entities.append(DttTargetDepth(coordinator, device_id))
            entities.append(DttTargetWindow(coordinator, device_id))
        for device_id in data.lkbx_devices:
            entities.append(LkbxDurationModify(coordinator, device_id))
    async_add_entities(entities)


class DttTargetDepth(
    CoordinatorEntity[ResearchAndDesireCoordinator], NumberEntity
):
    """Number entity for DTT target depth."""

    _attr_has_entity_name = True
    _attr_translation_key = "dtt_target_depth_control"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "mm"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ResearchAndDesireCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"dtt_{device_id}_target_depth_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"dtt_{device_id}")},
            name="Deepthroat Trainer",
            manufacturer="Research and Desire",
            model="Deepthroat Trainer",
        )

    def _get_device_data(self) -> DttDeviceData | None:
        data = self.coordinator.data
        return data.dtt_devices.get(self._device_id) if data else None

    @property
    def native_value(self) -> float | None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return None
        return dd.active_template.get("targetDepth")

    async def async_set_native_value(self, value: float) -> None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return
        template_id = dd.active_template.get("id")
        if template_id is None:
            return
        try:
            await self.coordinator.client.async_update_dtt_template(template_id, targetDepth=value)
            await self.coordinator.async_request_refresh()
        except ApiError as err:
            _LOGGER.error("Failed to update target depth: %s", err)


class DttTargetWindow(
    CoordinatorEntity[ResearchAndDesireCoordinator], NumberEntity
):
    """Number entity for DTT target window."""

    _attr_has_entity_name = True
    _attr_translation_key = "dtt_target_window_control"
    _attr_native_min_value = 0.1
    _attr_native_max_value = 50
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "mm"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ResearchAndDesireCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"dtt_{device_id}_target_window_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"dtt_{device_id}")},
            name="Deepthroat Trainer",
            manufacturer="Research and Desire",
            model="Deepthroat Trainer",
        )

    def _get_device_data(self) -> DttDeviceData | None:
        data = self.coordinator.data
        return data.dtt_devices.get(self._device_id) if data else None

    @property
    def native_value(self) -> float | None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return None
        return dd.active_template.get("targetWindow")

    async def async_set_native_value(self, value: float) -> None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return
        template_id = dd.active_template.get("id")
        if template_id is None:
            return
        try:
            await self.coordinator.client.async_update_dtt_template(template_id, targetWindow=value)
            await self.coordinator.async_request_refresh()
        except ApiError as err:
            _LOGGER.error("Failed to update target window: %s", err)


class LkbxDurationModify(
    CoordinatorEntity[ResearchAndDesireCoordinator], NumberEntity
):
    """Number entity to modify the active lockbox session duration."""

    _attr_has_entity_name = True
    _attr_translation_key = "lkbx_duration_control"
    _attr_native_min_value = 60
    _attr_native_max_value = 2592000  # 30 days
    _attr_native_step = 60
    _attr_native_unit_of_measurement = "s"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ResearchAndDesireCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"lkbx_{device_id}_duration_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"lkbx_{device_id}")},
            name="Lockbox",
            manufacturer="Research and Desire",
            model="Lockbox",
        )

    def _get_device_data(self) -> LkbxDeviceData | None:
        data = self.coordinator.data
        return data.lkbx_devices.get(self._device_id) if data else None

    @property
    def native_value(self) -> float | None:
        dd = self._get_device_data()
        if dd is None or dd.active_session is None:
            return None
        return dd.active_session.get("duration")

    @property
    def available(self) -> bool:
        dd = self._get_device_data()
        return dd is not None and dd.active_template is not None

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.coordinator.client.async_lkbx_modify_session(int(value))
            await self.coordinator.async_request_refresh()
        except ApiError as err:
            _LOGGER.error("Failed to modify lock duration: %s", err)
