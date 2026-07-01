"""Constants for RTS Smart Covers."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "rts_smart_covers"
PLATFORMS = [Platform.COVER]

CONF_SOURCE_COVER = "source_cover"
CONF_TRAVEL_TIME = "travel_time"
CONF_INITIAL_POSITION = "initial_position"

DEFAULT_NAME = "RTS Smart Cover"
DEFAULT_TRAVEL_TIME = 35.0
DEFAULT_INITIAL_POSITION = 100

MIN_TRAVEL_TIME = 1.0
MAX_TRAVEL_TIME = 300.0
