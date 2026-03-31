"""Lock platform for Research and Desire Lockbox."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ResearchAndDesireConfigEntry
from .api import ApiError
from .const import DOMAIN
from .coordinator import LkbxDeviceData, ResearchAndDesireCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lockbox lock entities."""
    coordinator: ResearchAndDesireCoordinator = entry.runtime_data
    entities: list[LockEntity] = []
    data = coordinator.data
    if data:
        for device_id in data.lkbx_devices:
            entities.append(ResearchAndDesireLock(coordinator, device_id))
    async_add_entities(entities)


class ResearchAndDesireLock(
    CoordinatorEntity[ResearchAndDesireCoordinator], LockEntity
):
    """Lock entity for the Research and Desire Lockbox."""

    _attr_has_entity_name = True
    _attr_translation_key = "lkbx_lock"

    def __init__(
        self,
        coordinator: ResearchAndDesireCoordinator,
        device_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"lkbx_{device_id}_lock"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"lkbx_{device_id}")},
            name="Lockbox",
            manufacturer="Research and Desire",
            model="Lockbox",
        )

    def _get_device_data(self) -> LkbxDeviceData | None:
        data = self.coordinator.data
        if data is None:
            return None
        return data.lkbx_devices.get(self._device_id)

    @property
    def is_locked(self) -> bool | None:
        device_data = self._get_device_data()
        if device_data is None:
            return None
        return device_data.active_template is not None

    @property
    def is_locking(self) -> bool:
        device_data = self._get_device_data()
        if device_data is None or device_data.active_session is None:
            return False
        return device_data.active_session.get("lockState") == "pending"

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lockbox using the first available template."""
        device_data = self._get_device_data()
        if device_data is None:
            return

        templates = device_data.templates
        if not templates:
            _LOGGER.error("No lock templates available")
            return

        template_id = templates[0].get("id")
        if template_id is None:
            _LOGGER.error("Lock template has no ID")
            return

        try:
            await self.coordinator.client.async_lkbx_lock(template_id)
            await self.coordinator.async_request_refresh()
        except ApiError as err:
            _LOGGER.error("Failed to lock: %s", err)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lockbox."""
        try:
            await self.coordinator.client.async_lkbx_unlock()
            await self.coordinator.async_request_refresh()
        except ApiError as err:
            _LOGGER.error("Failed to unlock: %s", err)
