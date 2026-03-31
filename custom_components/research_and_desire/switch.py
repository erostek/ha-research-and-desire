"""Switch platform for Research and Desire."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ResearchAndDesireConfigEntry
from .api import ApiError
from .const import DOMAIN
from .coordinator import DttDeviceData, ResearchAndDesireCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: ResearchAndDesireCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = []
    data = coordinator.data
    if data:
        for device_id in data.dtt_devices:
            entities.append(DttHandsFreeMode(coordinator, device_id))
    async_add_entities(entities)


class DttHandsFreeMode(
    CoordinatorEntity[ResearchAndDesireCoordinator], SwitchEntity
):
    """Switch entity for DTT hands-free mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "dtt_hands_free_mode"

    def __init__(self, coordinator: ResearchAndDesireCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"dtt_{device_id}_hands_free_mode"
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
    def is_on(self) -> bool | None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return None
        return dd.active_template.get("handsFreeMode")

    async def _set_hands_free(self, value: bool) -> None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return
        template_id = dd.active_template.get("id")
        if template_id is None:
            return
        try:
            await self.coordinator.client.async_update_dtt_template(template_id, handsFreeMode=value)
            await self.coordinator.async_request_refresh()
        except ApiError as err:
            _LOGGER.error("Failed to update hands-free mode: %s", err)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_hands_free(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_hands_free(False)
