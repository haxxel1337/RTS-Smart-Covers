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

## Reconfigure

You can reconfigure an existing RTS Smart Cover from the Home Assistant integration settings.

Reconfigure can update:

- Smart cover name
- Travel time
- Initial assumed position

The source cover is used as the config entry unique ID and cannot be changed in-place.
To use another source cover, remove the existing RTS Smart Cover entry and create a new one.
