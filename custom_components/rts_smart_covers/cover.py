"""Cover platform for RTS Smart Covers."""

from __future__ import annotations

from time import monotonic
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_INITIAL_POSITION,
    CONF_SOURCE_COVER,
    CONF_TRAVEL_TIME,
    DATA_ENTITIES,
    DEFAULT_INITIAL_POSITION,
    DEFAULT_TRAVEL_TIME,
    DOMAIN,
)

SOURCE_SERVICE_OPEN_COVER = "open_cover"
SOURCE_SERVICE_CLOSE_COVER = "close_cover"
SOURCE_SERVICE_STOP_COVER = "stop_cover"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RTS Smart Covers cover entity."""
    async_add_entities([RtsSmartCoverEntity(hass, entry)])


class RtsSmartCoverEntity(CoverEntity, RestoreEntity):
    """Time-based virtual cover for RTS covers without position feedback."""

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
        """Initialize the RTS Smart Cover entity."""
        self.hass = hass
        self._entry = entry
        self._source_cover = entry.data[CONF_SOURCE_COVER]
        self._travel_time = float(entry.data.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME))
        self._position = self._clamp(float(entry.data.get(CONF_INITIAL_POSITION, DEFAULT_INITIAL_POSITION)))
        self._direction: int | None = None
        self._target_position: float | None = None
        self._started_position: float | None = None
        self._started_at: float | None = None
        self._auto_stop_unsub = None
        self._tick_unsub = None
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = f"{DOMAIN}_{self._source_cover.replace('.', '_')}"

    async def async_added_to_hass(self) -> None:
        """Restore the last assumed position and register entity."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            restored_position = last_state.attributes.get("current_position")
            if restored_position is not None:
                self._position = self._clamp(float(restored_position))
            elif last_state.state == "closed":
                self._position = 0.0
            elif last_state.state == "open":
                self._position = 100.0

        self.hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTITIES, {})[self.entity_id] = self
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._source_cover], self._handle_source_state_change)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up timers and entity registry when removed."""
        self._clear_timers()
        self.hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTITIES, {}).pop(self.entity_id, None)

    @callback
    def _handle_source_state_change(self, event: Any) -> None:
        """Update availability when the source cover changes."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return whether the source cover is available."""
        state = self.hass.states.get(self._source_cover)
        return state is not None and state.state not in {STATE_UNAVAILABLE, STATE_UNKNOWN}

    @property
    def current_cover_position(self) -> int:
        """Return the current assumed cover position."""
        return round(self._estimated_position())

    @property
    def is_closed(self) -> bool:
        """Return whether the cover is fully closed."""
        return self.current_cover_position <= 0

    @property
    def is_opening(self) -> bool:
        """Return whether the cover is currently opening."""
        return self._direction == 1

    @property
    def is_closing(self) -> bool:
        """Return whether the cover is currently closing."""
        return self._direction == -1

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "source_cover": self._source_cover,
            "travel_time": self._travel_time,
            "target_position": self._target_position,
            "assumed_position": round(self._estimated_position()),
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover fully."""
        await self._async_move_to(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover fully."""
        await self._async_move_to(0)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover and store the current assumed position."""
        await self._async_stop_and_store(send_stop=True)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a target position."""
        await self._async_move_to(float(kwargs[ATTR_POSITION]))

    async def async_set_known_position(self, position: int) -> None:
        """Set known position without moving the physical cover."""
        if self._direction is not None:
            await self._async_stop_and_store(send_stop=True)
        else:
            self._clear_timers()

        self._position = self._clamp(float(position))
        self._direction = None
        self._target_position = None
        self._started_position = None
        self._started_at = None
        self.async_write_ha_state()

    async def async_mark_open(self) -> None:
        """Mark the cover as fully open without moving it."""
        await self.async_set_known_position(100)

    async def async_mark_closed(self) -> None:
        """Mark the cover as fully closed without moving it."""
        await self.async_set_known_position(0)

    async def _async_move_to(self, target_position: float) -> None:
        """Move the cover to a target position using travel time math."""
        target_position = self._clamp(target_position)
        if self._direction is not None:
            await self._async_stop_and_store(send_stop=True)

        current_position = self._position
        difference = target_position - current_position
        if abs(difference) < 0.5:
            self._position = target_position
            self._target_position = None
            self.async_write_ha_state()
            return

        duration = abs(difference) / 100 * self._travel_time
        direction = 1 if difference > 0 else -1
        service = SOURCE_SERVICE_OPEN_COVER if direction == 1 else SOURCE_SERVICE_CLOSE_COVER

        self._direction = direction
        self._target_position = target_position
        self._started_position = current_position
        self._started_at = monotonic()

        self.async_write_ha_state()
        await self._async_source_call(service)
        self._schedule_auto_stop(duration, target_position)
        self._schedule_tick()

    async def _async_finish_move(self, target_position: float) -> None:
        """Finish a timed movement and stop the source cover."""
        if self._direction is None:
            return

        self._position = self._clamp(target_position)
        self._clear_timers()
        self._direction = None
        self._target_position = None
        self._started_position = None
        self._started_at = None
        await self._async_source_call(SOURCE_SERVICE_STOP_COVER)
        self.async_write_ha_state()

    async def _async_stop_and_store(self, send_stop: bool) -> None:
        """Stop movement and store the estimated position."""
        was_moving = self._direction is not None
        self._position = self._clamp(self._estimated_position())
        self._clear_timers()
        self._direction = None
        self._target_position = None
        self._started_position = None
        self._started_at = None
        if send_stop and was_moving:
            await self._async_source_call(SOURCE_SERVICE_STOP_COVER)
        self.async_write_ha_state()

    async def _async_source_call(self, service: str) -> None:
        """Call a service on the physical/source cover."""
        await self.hass.services.async_call(
            "cover",
            service,
            {"entity_id": self._source_cover},
            blocking=True,
        )

    def _estimated_position(self) -> float:
        """Calculate the current assumed position."""
        if self._direction is None or self._started_at is None or self._started_position is None:
            return self._position

        elapsed = monotonic() - self._started_at
        moved_percent = elapsed / self._travel_time * 100
        estimated = self._started_position + (moved_percent * self._direction)

        if self._target_position is not None:
            if self._direction == 1:
                estimated = min(estimated, self._target_position)
            else:
                estimated = max(estimated, self._target_position)

        return self._clamp(estimated)

    @callback
    def _schedule_auto_stop(self, duration: float, target_position: float) -> None:
        """Schedule automatic stop at the calculated target time."""
        self._clear_auto_stop_timer()

        @callback
        def _auto_stop_callback(now: Any) -> None:
            self._auto_stop_unsub = None
            self.hass.async_create_task(self._async_finish_move(target_position))

        self._auto_stop_unsub = async_call_later(self.hass, duration, _auto_stop_callback)

    @callback
    def _schedule_tick(self) -> None:
        """Schedule the next UI update while moving."""
        self._clear_tick_timer()

        @callback
        def _tick_callback(now: Any) -> None:
            self._tick_unsub = None
            if self._direction is None:
                return
            self.async_write_ha_state()
            self._schedule_tick()

        self._tick_unsub = async_call_later(self.hass, 1, _tick_callback)

    @callback
    def _clear_auto_stop_timer(self) -> None:
        """Clear the automatic stop timer."""
        if self._auto_stop_unsub is not None:
            self._auto_stop_unsub()
            self._auto_stop_unsub = None

    @callback
    def _clear_tick_timer(self) -> None:
        """Clear the UI tick timer."""
        if self._tick_unsub is not None:
            self._tick_unsub()
            self._tick_unsub = None

    @callback
    def _clear_timers(self) -> None:
        """Clear all timers."""
        self._clear_auto_stop_timer()
        self._clear_tick_timer()

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp a position value to Home Assistant's 0-100 cover range."""
        return min(100.0, max(0.0, value))
