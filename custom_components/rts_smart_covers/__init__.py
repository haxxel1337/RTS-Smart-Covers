"""RTS Smart Covers custom integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DATA_ENTITIES,
    DOMAIN,
    PLATFORMS,
    SERVICE_MARK_CLOSED,
    SERVICE_MARK_OPEN,
    SERVICE_SET_KNOWN_POSITION,
)

_SERVICE_ENTITY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    },
    extra=vol.ALLOW_EXTRA,
)

_SERVICE_SET_KNOWN_POSITION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required("position"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    },
    extra=vol.ALLOW_EXTRA,
)


def _entity_ids_from_call(call: ServiceCall) -> list[str]:
    """Extract entity IDs from service data."""
    entity_ids = call.data.get(ATTR_ENTITY_ID)
    if entity_ids is None:
        return []
    if isinstance(entity_ids, str):
        return [entity_ids]
    return list(entity_ids)


async def _async_call_smart_cover_entities(
    hass: HomeAssistant,
    call: ServiceCall,
    method_name: str,
    *args: Any,
) -> None:
    """Call a method on selected RTS Smart Cover entities."""
    entities = hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTITIES, {})
    entity_ids = _entity_ids_from_call(call)

    if entity_ids:
        target_entities = [entities[entity_id] for entity_id in entity_ids if entity_id in entities]
    else:
        target_entities = list(entities.values())

    if not target_entities:
        raise HomeAssistantError(
            "No RTS Smart Covers matched the service target. Select one or more rts_smart_covers cover entities."
        )

    for entity in target_entities:
        method = getattr(entity, method_name)
        await method(*args)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up RTS Smart Covers services."""
    hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTITIES, {})

    if not hass.services.has_service(DOMAIN, SERVICE_SET_KNOWN_POSITION):

        async def handle_set_known_position(call: ServiceCall) -> None:
            await _async_call_smart_cover_entities(
                hass,
                call,
                "async_set_known_position",
                call.data["position"],
            )

        async def handle_mark_open(call: ServiceCall) -> None:
            await _async_call_smart_cover_entities(hass, call, "async_mark_open")

        async def handle_mark_closed(call: ServiceCall) -> None:
            await _async_call_smart_cover_entities(hass, call, "async_mark_closed")

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_KNOWN_POSITION,
            handle_set_known_position,
            schema=_SERVICE_SET_KNOWN_POSITION_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_MARK_OPEN,
            handle_mark_open,
            schema=_SERVICE_ENTITY_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_MARK_CLOSED,
            handle_mark_closed,
            schema=_SERVICE_ENTITY_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RTS Smart Covers from a config entry."""
    hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTITIES, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an RTS Smart Covers config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
