"""The Research and Desire integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ResearchAndDesireApiClient
from .const import CONF_API_KEY, PLATFORMS
from .coordinator import ResearchAndDesireCoordinator

type ResearchAndDesireConfigEntry = ConfigEntry[ResearchAndDesireCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: ResearchAndDesireConfigEntry
) -> bool:
    """Set up Research and Desire from a config entry."""
    session = async_get_clientsession(hass)
    client = ResearchAndDesireApiClient(session, entry.data[CONF_API_KEY])

    coordinator = ResearchAndDesireCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ResearchAndDesireConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
