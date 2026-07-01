"""Cover platform for RTS Smart Covers."""
from __future__ import annotations

import logging
from time import monotonic
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_INITIAL_POSITION,
    CONF_SOURCE_COVER,
    CONF_TRAVEL_TIME,
    DEFAULT_INITIAL_POSITION,
    DEFAULT_NAME,
    DEFAULT_TRAVEL_TIME,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RTS Smart Covers entities."""
    async_add_entities([RtsSmartCoverEntity(hass, entry)])


class RtsSmartCoverEntity(CoverEntity, RestoreEntity):
    """Time-estimated cover built on top of an open/stop/close RTS cover."""

    _attr_assumed_state = True
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the smart cover."""
        self.hass = hass
        self.entry = entry

        data = {**entry.data, **entry.options}

        self._source_cover: str = data[CONF_SOURCE_COVER]
        self._travel_time: float = float(data.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME))
        self._position: float = self._clamp(
            float(data.get(CONF_INITIAL_POSITION, DEFAULT_INITIAL_POSITION))
        )

        self._attr_name = data.get(CONF_NAME, DEFAULT_NAME)
        self._attr_unique_id = f"{entry.entry_id}_rts_smart_cover"

        self._direction: str | None = None
        self._target_position: float | None = None
        self._started_position: float = self._position
        self._started_at: float | None = None

        self._auto_stop_unsub = None
        self._tick_unsub = None


    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending timers when Home Assistant removes the entity."""
        self._clear_timers()

    async def async_added_to_hass(self) -> None:
        """Restore the last assumed position after Home Assistant restart."""
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        restored_position = last_state.attributes.get("current_position")

        if restored_position is None:
            if last_state.state == "closed":
                restored_position = 0
            elif last_state.state == "open":
                restored_position = 100

        if restored_position is None:
            return

        try:
            self._position = self._clamp(float(restored_position))
            _LOGGER.debug(
                "Restored %s assumed position to %.1f",
                self.entity_id,
                self._position,
            )
        except (TypeError, ValueError):
            _LOGGER.debug("Could not restore position from %r", restored_position)

    @property
    def available(self) -> bool:
        """Return whether the source cover is available."""
        source_state = self.hass.states.get(self._source_cover)
        return source_state is not None and source_state.state not in {
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        }

    @property
    def current_cover_position(self) -> int:
        """Return current estimated position, where 0 is closed and 100 is open."""
        return round(self._estimated_position())

    @property
    def is_closed(self) -> bool:
        """Return true if the cover is fully closed."""
        return self.current_cover_position <= 0

    @property
    def is_opening(self) -> bool:
        """Return true if the cover is opening."""
        return self._direction == "opening"

    @property
    def is_closing(self) -> bool:
        """Return true if the cover is closing."""
        return self._direction == "closing"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "source_cover": self._source_cover,
            "travel_time": self._travel_time,
            "target_position": self._target_position,
            "assumed_position": True,
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover fully."""
        await self._async_move_to(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover fully."""
        await self._async_move_to(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to the requested position."""
        position = kwargs.get(ATTR_POSITION)
        if position is None:
            return

        await self._async_move_to(float(position))

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover and store the current estimated position."""
        await self._async_stop_and_store(send_stop=True)

    async def async_set_known_position(self, position: int) -> None:
        """Set the assumed position of the cover without moving it."""
        was_moving = self._direction is not None
        self._clear_timers()

        if was_moving:
            await self._async_source_call(SERVICE_STOP_COVER)

        self._position = self._clamp(position)
        self._direction = None
        self._target_position = None
        self._started_at = None

        self.async_write_ha_state()

    async def async_mark_open(self) -> None:
        """Mark the cover as fully open without moving it."""
        await self.async_set_known_position(100)

    async def async_mark_closed(self) -> None:
        """Mark the cover as fully closed without moving it."""
        await self.async_set_known_position(0)

    async def _async_move_to(self, target_position: float) -> None:
        """Move the cover to a position by timing open/close then sending stop."""
        target_position = self._clamp(target_position)

        if self._direction is not None:
            await self._async_stop_and_store(send_stop=True)

        current_position = self._clamp(self._position)
        difference = target_position - current_position

        if abs(difference) < 0.5:
            self._position = target_position
            self._direction = None
            self._target_position = None
            self._started_at = None
            self.async_write_ha_state()
            return

        duration = abs(difference) / 100 * self._travel_time

        self._direction = "opening" if difference > 0 else "closing"
        self._target_position = target_position
        self._started_position = current_position
        self._started_at = monotonic()

        service = SERVICE_OPEN_COVER if self._direction == "opening" else SERVICE_CLOSE_COVER

        _LOGGER.debug(
            "%s moving from %.1f to %.1f using %s for %.2fs",
            self.entity_id,
            current_position,
            target_position,
            service,
            duration,
        )

        self.async_write_ha_state()
        await self._async_source_call(service)

        @callback
        def _auto_stop_callback(_now) -> None:
            self.hass.async_create_task(self._async_finish_move(target_position))

        self._auto_stop_unsub = async_call_later(
            self.hass,
            duration,
            _auto_stop_callback,
        )
        self._schedule_tick()

    async def _async_finish_move(self, target_position: float) -> None:
        """Finish timed movement and stop at the target position."""
        self._position = self._clamp(target_position)
        self._clear_timers()

        await self._async_source_call(SERVICE_STOP_COVER)

        _LOGGER.debug("%s reached target %.1f", self.entity_id, self._position)

        self._direction = None
        self._target_position = None
        self._started_at = None

        self.async_write_ha_state()

    async def _async_stop_and_store(self, *, send_stop: bool) -> None:
        """Stop movement, store the current estimated position, and clear timers."""
        self._position = self._estimated_position()
        was_moving = self._direction is not None

        self._clear_timers()

        if send_stop and was_moving:
            await self._async_source_call(SERVICE_STOP_COVER)

        _LOGGER.debug(
            "%s stopped at estimated position %.1f",
            self.entity_id,
            self._position,
        )

        self._direction = None
        self._target_position = None
        self._started_at = None

        self.async_write_ha_state()

    async def _async_source_call(self, service: str) -> None:
        """Call a cover service on the source cover."""
        await self.hass.services.async_call(
            "cover",
            service,
            {"entity_id": self._source_cover},
            blocking=True,
        )

    def _estimated_position(self) -> float:
        """Return the current estimated position."""
        if self._direction is None or self._started_at is None:
            return self._clamp(self._position)

        elapsed = max(0.0, monotonic() - self._started_at)
        moved_pct = elapsed / self._travel_time * 100

        if self._direction == "opening":
            return self._clamp(self._started_position + moved_pct)

        return self._clamp(self._started_position - moved_pct)

    def _schedule_tick(self) -> None:
        """Update Home Assistant state once per second while moving."""
        self._cancel_tick_timer()

        @callback
        def _tick(_now) -> None:
            self._tick_unsub = None

            if self._direction is None:
                return

            self.async_write_ha_state()
            self._schedule_tick()

        self._tick_unsub = async_call_later(self.hass, 1, _tick)

    def _clear_timers(self) -> None:
        """Cancel all timers."""
        self._cancel_auto_stop_timer()
        self._cancel_tick_timer()

    def _cancel_auto_stop_timer(self) -> None:
        """Cancel the pending auto-stop timer."""
        if self._auto_stop_unsub is not None:
            self._auto_stop_unsub()
            self._auto_stop_unsub = None

    def _cancel_tick_timer(self) -> None:
        """Cancel the UI tick timer."""
        if self._tick_unsub is not None:
            self._tick_unsub()
            self._tick_unsub = None

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp a cover position to the Home Assistant 0-100 range."""
        return max(0.0, min(100.0, value))
