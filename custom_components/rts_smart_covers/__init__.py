"""RTS Smart Covers custom integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import async_register_platform_entity_service

from .const import PLATFORMS


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up RTS Smart Covers integration services."""
    async_register_platform_entity_service(
        hass,
        "cover",
        "set_known_position",
        {"position": vol.Coerce(int)},
        "async_set_known_position",
    )
    async_register_platform_entity_service(
        hass,
        "cover",
        "mark_open",
        None,
        "async_mark_open",
    )
    async_register_platform_entity_service(
        hass,
        "cover",
        "mark_closed",
        None,
        "async_mark_closed",
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RTS Smart Covers from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
