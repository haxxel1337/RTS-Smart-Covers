#!/usr/bin/env python3
"""
Patch RTS Smart Covers repo in-place.

Place this file in:
C:\\Users\\axelh\\Dropbox\\Axels mapp\\Coding Projects\\RTS-Smart-Covers

Then run:
python patch_rts_smart_covers_v0_3_x.py

It rewrites the integration files with proper LF newlines, preserves brand images,
adds services.yaml, fixes .gitignore, updates tests, and bumps manifest.json patch
version by +0.0.1.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

DOMAIN = "rts_smart_covers"
ROOT = Path(__file__).resolve().parent
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN
BRAND_DIR = INTEGRATION_DIR / "brand"
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.strip("\n").replace("\r\n", "\n").replace("\r", "\n") + "\n"
    path.write_text(normalized, encoding="utf-8", newline="\n")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def next_patch_version(current: str | None) -> str:
    if not current:
        return "0.3.2"
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(current).strip())
    if not match:
        return "0.3.2"
    major, minor, patch = (int(part) for part in match.groups())
    return f"{major}.{minor}.{patch + 1}"


def ensure_brand_images() -> None:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    root_brand = ROOT / "brand"
    if root_brand.exists() and root_brand.is_dir():
        for filename in ("logo.png", "icon.png"):
            source = root_brand / filename
            target = BRAND_DIR / filename
            if source.exists() and not target.exists():
                shutil.move(str(source), str(target))
        try:
            if not any(root_brand.iterdir()):
                root_brand.rmdir()
        except OSError:
            pass
    gitkeep = BRAND_DIR / ".gitkeep"
    if not gitkeep.exists():
        write_text(gitkeep, "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", help="Set a specific manifest version instead of patch-bumping current version.")
    parser.add_argument("--no-bump", action="store_true", help="Keep current manifest version. Not recommended for release commits.")
    args = parser.parse_args()

    if ROOT.name != "RTS-Smart-Covers":
        print(f"WARNING: running from {ROOT}")
        print("Expected folder name: RTS-Smart-Covers")
        print("Continuing anyway.\n")

    ensure_brand_images()

    current_manifest = read_json(INTEGRATION_DIR / "manifest.json")
    current_version = current_manifest.get("version")
    if args.version:
        new_version = args.version
    elif args.no_bump:
        new_version = current_version or "0.3.2"
    else:
        new_version = next_patch_version(current_version)

    write_text(ROOT / ".gitignore", r'''
# Python cache
__pycache__/
*.py[cod]
*$py.class

# Test / lint / type-check caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
env/
ENV/

# Build artifacts
build/
dist/
*.egg-info/

# IDE / editor
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Local env/secrets
.env
.env.*
*.local

# Logs
*.log

# Temporary files
*.tmp
*.bak
*.old

# Home Assistant local runtime/config junk if ever copied into repo
.storage/
.homeassistant/
deps/
tts/
known_devices.yaml
home-assistant.log*
OZW_Log.txt
ip_bans.yaml
''')

    write_text(ROOT / "hacs.json", json.dumps({
        "name": "RTS Smart Covers",
        "render_readme": True,
        "domains": ["cover"],
        "homeassistant": "2026.6.1",
    }, indent=2, ensure_ascii=False))

    write_text(ROOT / "README.md", r'''
# RTS Smart Covers

A Home Assistant custom integration for adding assumed position control to Somfy RTS / RFXtrx covers that only support open, close and stop.

RTS covers usually do not report a real position. This integration creates a virtual smart cover that estimates the current position by timing movement.

## Features

- Adds a normal Home Assistant `cover` entity
- Supports `open_cover`, `close_cover`, `stop_cover` and `set_cover_position`
- Uses Home Assistant's standard position scale: `0 = closed`, `100 = open`
- `30%` means 30% open and 70% closed
- Restores the last assumed position after restart
- Updates the UI roughly once per second while moving
- Automatically sends stop when the calculated travel time has elapsed
- Includes calibration services:
  - `rts_smart_covers.set_known_position`
  - `rts_smart_covers.mark_open`
  - `rts_smart_covers.mark_closed`

## Example

If the travel time is 35 seconds:

- From 100 to 30: close for 24.5 seconds, then stop
- From 0 to 30: open for 10.5 seconds, then stop
- From 30 to 70: open for 14 seconds, then stop

## Installation with HACS

1. Add this repository as a custom HACS repository.
2. Category: Integration.
3. Install **RTS Smart Covers**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration**.
6. Search for **RTS Smart Covers**.

## Configuration

The config flow asks for:

- Source cover, for example `cover.officesoversleft2`
- Smart cover name
- Full travel time in seconds
- Initial assumed position

## Brand assets

Local brand assets should be placed here:

```text
custom_components/rts_smart_covers/brand/logo.png
custom_components/rts_smart_covers/brand/icon.png
```
''')

    write_text(ROOT / "LICENSE", r'''
MIT License

Copyright (c) 2026 Axel Holmstedt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')

    write_text(INTEGRATION_DIR / "manifest.json", json.dumps({
        "domain": DOMAIN,
        "name": "RTS Smart Covers",
        "codeowners": ["@haxxel1337"],
        "config_flow": True,
        "documentation": "https://github.com/haxxel1337/RTS-Smart-Covers",
        "issue_tracker": "https://github.com/haxxel1337/RTS-Smart-Covers/issues",
        "iot_class": "local_push",
        "version": new_version,
    }, indent=2, ensure_ascii=False))

    write_text(INTEGRATION_DIR / "const.py", r'''
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

DATA_ENTITIES = "entities"

SERVICE_SET_KNOWN_POSITION = "set_known_position"
SERVICE_MARK_OPEN = "mark_open"
SERVICE_MARK_CLOSED = "mark_closed"
''')

    write_text(INTEGRATION_DIR / "__init__.py", r'''
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
''')

    write_text(INTEGRATION_DIR / "config_flow.py", r'''
"""Config flow for RTS Smart Covers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_INITIAL_POSITION,
    CONF_SOURCE_COVER,
    CONF_TRAVEL_TIME,
    DEFAULT_INITIAL_POSITION,
    DEFAULT_NAME,
    DEFAULT_TRAVEL_TIME,
    DOMAIN,
    MAX_TRAVEL_TIME,
    MIN_TRAVEL_TIME,
)


def _data_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the config flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_COVER, default=defaults.get(CONF_SOURCE_COVER)): EntitySelector(
                EntitySelectorConfig(domain="cover")
            ),
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
            vol.Required(CONF_TRAVEL_TIME, default=defaults.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME)): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_TRAVEL_TIME,
                    max=MAX_TRAVEL_TIME,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_INITIAL_POSITION,
                default=defaults.get(CONF_INITIAL_POSITION, DEFAULT_INITIAL_POSITION),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    )


class RtsSmartCoversConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTS Smart Covers."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SOURCE_COVER])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_data_schema(), errors={})

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        config_entry = self._get_reconfigure_entry()

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SOURCE_COVER])
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(config_entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_data_schema(dict(config_entry.data)),
            errors={},
        )
''')

    write_text(INTEGRATION_DIR / "cover.py", r'''
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
''')

    write_text(INTEGRATION_DIR / "services.yaml", r'''
set_known_position:
  name: Set known position
  description: Set the assumed position of an RTS Smart Cover without moving the physical cover.
  target:
    entity:
      integration: rts_smart_covers
      domain: cover
  fields:
    position:
      name: Position
      description: Known cover position where 0 is fully closed and 100 is fully open.
      required: true
      selector:
        number:
          min: 0
          max: 100
          step: 1
          unit_of_measurement: "%"

mark_open:
  name: Mark open
  description: Mark an RTS Smart Cover as fully open without moving the physical cover.
  target:
    entity:
      integration: rts_smart_covers
      domain: cover

mark_closed:
  name: Mark closed
  description: Mark an RTS Smart Cover as fully closed without moving the physical cover.
  target:
    entity:
      integration: rts_smart_covers
      domain: cover
''')

    strings = {
        "config": {
            "step": {
                "user": {
                    "title": "RTS Smart Covers",
                    "description": "Create a smart timed cover for an RTS/RFXtrx cover.",
                    "data": {
                        "source_cover": "Source cover",
                        "name": "Smart cover name",
                        "travel_time": "Full travel time",
                        "initial_position": "Initial assumed position",
                    },
                },
                "reconfigure": {
                    "title": "Reconfigure RTS Smart Cover",
                    "description": "Update the source cover, name, travel time or assumed position.",
                    "data": {
                        "source_cover": "Source cover",
                        "name": "Smart cover name",
                        "travel_time": "Full travel time",
                        "initial_position": "Initial assumed position",
                    },
                },
            },
            "abort": {
                "already_configured": "This source cover is already configured.",
                "reconfigure_successful": "RTS Smart Cover reconfiguration complete.",
            },
        }
    }
    write_text(INTEGRATION_DIR / "strings.json", json.dumps(strings, indent=2, ensure_ascii=False))

    en = strings
    sv = {
        "config": {
            "step": {
                "user": {
                    "title": "RTS Smart Covers",
                    "description": "Skapa en smart tidsbaserad cover för en RTS/RFXtrx-cover.",
                    "data": {
                        "source_cover": "Käll-cover",
                        "name": "Namn på smart cover",
                        "travel_time": "Full gångtid",
                        "initial_position": "Initial antagen position",
                    },
                },
                "reconfigure": {
                    "title": "Konfigurera om RTS Smart Cover",
                    "description": "Uppdatera käll-cover, namn, gångtid eller antagen position.",
                    "data": {
                        "source_cover": "Käll-cover",
                        "name": "Namn på smart cover",
                        "travel_time": "Full gångtid",
                        "initial_position": "Initial antagen position",
                    },
                },
            },
            "abort": {
                "already_configured": "Den här käll-covern är redan konfigurerad.",
                "reconfigure_successful": "RTS Smart Cover har konfigurerats om.",
            },
        }
    }
    write_text(TRANSLATIONS_DIR / "en.json", json.dumps(en, indent=2, ensure_ascii=False))
    write_text(TRANSLATIONS_DIR / "sv.json", json.dumps(sv, indent=2, ensure_ascii=False))

    write_text(ROOT / "test_rts_smart_covers_project.py", r'''
"""Static project tests for RTS Smart Covers."""

from __future__ import annotations

import ast
import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAIN = "rts_smart_covers"
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_count(path: Path) -> int:
    return len(read(path).splitlines())


def load_json(path: Path) -> dict:
    return json.loads(read(path))


def test_required_files() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "hacs.json",
        ROOT / "LICENSE",
        ROOT / ".gitignore",
        INTEGRATION_DIR / "__init__.py",
        INTEGRATION_DIR / "manifest.json",
        INTEGRATION_DIR / "const.py",
        INTEGRATION_DIR / "config_flow.py",
        INTEGRATION_DIR / "cover.py",
        INTEGRATION_DIR / "services.yaml",
        INTEGRATION_DIR / "strings.json",
        INTEGRATION_DIR / "translations" / "en.json",
        INTEGRATION_DIR / "translations" / "sv.json",
        INTEGRATION_DIR / "brand" / ".gitkeep",
    ]
    for path in required:
        assert_true(path.exists(), f"Missing required file: {path}")
    assert_true(not (ROOT / "brand").exists(), "Root brand/ folder must not exist")


def test_newlines() -> None:
    files = [
        ROOT / ".gitignore",
        INTEGRATION_DIR / "__init__.py",
        INTEGRATION_DIR / "const.py",
        INTEGRATION_DIR / "config_flow.py",
        INTEGRATION_DIR / "cover.py",
        INTEGRATION_DIR / "services.yaml",
    ]
    for path in files:
        assert_true(line_count(path) > 5, f"{path} looks minified or missing newlines")
    cover = read(INTEGRATION_DIR / "cover.py")
    assert_true(
        '"""Cover platform for RTS Smart Covers."""\n\nfrom __future__ import annotations' in cover,
        "cover.py must have module docstring followed by newline before future import",
    )


def test_json() -> None:
    manifest = load_json(INTEGRATION_DIR / "manifest.json")
    hacs = load_json(ROOT / "hacs.json")
    load_json(INTEGRATION_DIR / "strings.json")
    load_json(INTEGRATION_DIR / "translations" / "en.json")
    load_json(INTEGRATION_DIR / "translations" / "sv.json")
    assert_true(manifest["domain"] == DOMAIN, "manifest domain mismatch")
    assert_true(manifest["name"] == "RTS Smart Covers", "manifest name mismatch")
    assert_true(manifest["config_flow"] is True, "manifest config_flow must be true")
    assert_true(manifest["iot_class"] == "local_push", "manifest iot_class mismatch")
    assert_true(manifest["version"].count(".") == 2, "manifest version must be semver-like")
    assert_true(hacs["homeassistant"] == "2026.6.1", "hacs minimum HA version mismatch")
    assert_true("cover" in hacs["domains"], "hacs domains must include cover")


def test_python_compiles_and_ast() -> None:
    for path in [
        INTEGRATION_DIR / "__init__.py",
        INTEGRATION_DIR / "const.py",
        INTEGRATION_DIR / "config_flow.py",
        INTEGRATION_DIR / "cover.py",
    ]:
        py_compile.compile(str(path), doraise=True)
        ast.parse(read(path))


def test_cover_code_patterns() -> None:
    cover = read(INTEGRATION_DIR / "cover.py")
    required = [
        "CoverEntity",
        "RestoreEntity",
        "CoverDeviceClass.SHADE",
        "CoverEntityFeature.SET_POSITION",
        "current_cover_position",
        "async_set_cover_position",
        "async_call_later",
        "async_track_state_change_event",
        "monotonic",
        "STATE_UNAVAILABLE",
        "STATE_UNKNOWN",
        "async_set_known_position",
        "async_mark_open",
        "async_mark_closed",
        '"open_cover"',
        '"close_cover"',
        '"stop_cover"',
    ]
    for needle in required:
        assert_true(needle in cover, f"cover.py missing {needle}")
    forbidden = ["input_number.", "input_select.", "input_datetime.", "template:", "script."]
    for needle in forbidden:
        assert_true(needle not in cover, f"cover.py must not depend on {needle}")


def test_config_flow_patterns() -> None:
    config_flow = read(INTEGRATION_DIR / "config_flow.py")
    required = [
        "async_step_user",
        "async_step_reconfigure",
        "async_update_reload_and_abort",
        "_abort_if_unique_id_mismatch",
        "_abort_if_unique_id_configured",
        "EntitySelector",
        'EntitySelectorConfig(domain="cover")',
        "TextSelector",
        "NumberSelector",
        "NumberSelectorMode.BOX",
        "NumberSelectorMode.SLIDER",
    ]
    for needle in required:
        assert_true(needle in config_flow, f"config_flow.py missing {needle}")


def test_services() -> None:
    services = read(INTEGRATION_DIR / "services.yaml")
    init = read(INTEGRATION_DIR / "__init__.py")
    for service in ["set_known_position:", "mark_open:", "mark_closed:"]:
        assert_true(service in services, f"services.yaml missing {service}")
    for needle in [
        "hass.services.async_register",
        "SERVICE_SET_KNOWN_POSITION",
        "SERVICE_MARK_OPEN",
        "SERVICE_MARK_CLOSED",
        "async_set_known_position",
        "async_mark_open",
        "async_mark_closed",
    ]:
        assert_true(needle in init, f"__init__.py missing {needle}")


def test_timing_math() -> None:
    travel_time = 35.0
    assert_true(abs((abs(30 - 100) / 100 * travel_time) - 24.5) < 0.0001, "100->30 math failed")
    assert_true(abs((abs(30 - 0) / 100 * travel_time) - 10.5) < 0.0001, "0->30 math failed")
    assert_true(abs((abs(70 - 30) / 100 * travel_time) - 14.0) < 0.0001, "30->70 math failed")
    assert_true(abs((abs(0 - 70) / 100 * travel_time) - 24.5) < 0.0001, "70->0 math failed")
    assert_true(abs((abs(100 - 0) / 100 * travel_time) - 35.0) < 0.0001, "0->100 math failed")


def main() -> None:
    tests = [
        test_required_files,
        test_newlines,
        test_json,
        test_python_compiles_and_ast,
        test_cover_code_patterns,
        test_config_flow_patterns,
        test_services,
        test_timing_math,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("\nAll RTS Smart Covers static tests passed.")


if __name__ == "__main__":
    main()
''')

    print("RTS Smart Covers patch applied.")
    print(f"Root: {ROOT}")
    print(f"Manifest version: {current_version!r} -> {new_version!r}")
    print("\nNext commands:")
    print("python -m py_compile .\\custom_components\\rts_smart_covers\\__init__.py")
    print("python -m py_compile .\\custom_components\\rts_smart_covers\\config_flow.py")
    print("python -m py_compile .\\custom_components\\rts_smart_covers\\cover.py")
    print("python -m py_compile .\\custom_components\\rts_smart_covers\\const.py")
    print("python test_rts_smart_covers_project.py")
    print("git diff --check")
    print("git status")
    print(f'git add . && git commit -m "Fix newlines and release v{new_version}"')
    print(f"git tag v{new_version}")
    print("git push --follow-tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
