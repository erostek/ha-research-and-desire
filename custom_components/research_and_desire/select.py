"""Select platform for Research and Desire."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ResearchAndDesireConfigEntry
from .api import ApiError
from .const import DOMAIN
from .coordinator import DttDeviceData, LkbxDeviceData, ResearchAndDesireCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResearchAndDesireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator: ResearchAndDesireCoordinator = entry.runtime_data
    entities: list[SelectEntity] = []
    data = coordinator.data
    if data:
        for device_id in data.dtt_devices:
            entities.append(DttTemplateSelect(coordinator, device_id))
        for device_id in data.lkbx_devices:
            entities.append(LkbxTemplateSelect(coordinator, device_id))
    async_add_entities(entities)


class DttTemplateSelect(
    CoordinatorEntity[ResearchAndDesireCoordinator], SelectEntity
):
    """Select entity to choose and activate a DTT training template."""

    _attr_has_entity_name = True
    _attr_translation_key = "dtt_template_select"

    def __init__(self, coordinator: ResearchAndDesireCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"dtt_{device_id}_template_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"dtt_{device_id}")},
            name="Deepthroat Trainer",
            manufacturer="Research and Desire",
            model="Deepthroat Trainer",
        )

    def _get_device_data(self) -> DttDeviceData | None:
        data = self.coordinator.data
        return data.dtt_devices.get(self._device_id) if data else None

    def _get_templates(self) -> list[dict]:
        dd = self._get_device_data()
        if dd is None:
            return []
        return dd.all_templates or []

    @property
    def options(self) -> list[str]:
        return [t.get("name", f"Template {t.get('id')}") for t in self._get_templates()]

    @property
    def current_option(self) -> str | None:
        dd = self._get_device_data()
        if dd is None or dd.active_template is None:
            return None
        return dd.active_template.get("name")

    async def async_select_option(self, option: str) -> None:
        templates = self._get_templates()
        for t in templates:
            if t.get("name", f"Template {t.get('id')}") == option:
                template_id = t.get("id")
                if template_id is None:
                    return
                try:
                    await self.coordinator.client.async_activate_dtt_template(template_id)
                    await self.coordinator.async_request_refresh()
                except ApiError as err:
                    _LOGGER.error("Failed to activate template: %s", err)
                return


class LkbxTemplateSelect(
    CoordinatorEntity[ResearchAndDesireCoordinator], SelectEntity
):
    """Select entity to choose which lock template to use for locking."""

    _attr_has_entity_name = True
    _attr_translation_key = "lkbx_template_select"

    def __init__(self, coordinator: ResearchAndDesireCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._selected_template_id: int | None = None
        self._attr_unique_id = f"lkbx_{device_id}_template_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"lkbx_{device_id}")},
            name="Lockbox",
            manufacturer="Research and Desire",
            model="Lockbox",
        )

    def _get_device_data(self) -> LkbxDeviceData | None:
        data = self.coordinator.data
        return data.lkbx_devices.get(self._device_id) if data else None

    def _get_templates(self) -> list[dict]:
        dd = self._get_device_data()
        if dd is None:
            return []
        return dd.templates or []

    @property
    def options(self) -> list[str]:
        return [t.get("name", f"Template {t.get('id')}") for t in self._get_templates()]

    @property
    def current_option(self) -> str | None:
        dd = self._get_device_data()
        if dd is None:
            return None
        # If locked, show the active template
        if dd.active_template:
            return dd.active_template.get("name")
        # Otherwise show the selected template for next lock
        if self._selected_template_id is not None:
            for t in self._get_templates():
                if t.get("id") == self._selected_template_id:
                    return t.get("name")
        # Default to first template
        templates = self._get_templates()
        return templates[0].get("name") if templates else None

    @property
    def selected_template_id(self) -> int | None:
        """Get the currently selected template ID (used by the lock entity)."""
        if self._selected_template_id is not None:
            return self._selected_template_id
        templates = self._get_templates()
        return templates[0].get("id") if templates else None

    async def async_select_option(self, option: str) -> None:
        for t in self._get_templates():
            if t.get("name", f"Template {t.get('id')}") == option:
                self._selected_template_id = t.get("id")
                self.async_write_ha_state()
                return
