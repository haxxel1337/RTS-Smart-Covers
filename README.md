# RTS Smart Covers

RTS Smart Covers is a Home Assistant custom integration for covers that only support `open`, `stop` and `close`, such as Somfy RTS covers controlled through RFXtrx.

It creates a virtual smart cover with position support by estimating the position from the configured travel time.

> Svenska: Projektet är byggt för Somfy RTS/RFXtrx-covers där man normalt bara har öppna, stoppa och stäng, men vill få en smart cover med procent-slider i Home Assistant.

## Why this exists

Somfy RTS via RFXtrx usually has no real position feedback. Home Assistant can send commands, but it cannot know the true position of the cover.

This integration solves that by keeping an assumed position in software:

- `0%` = fully closed
- `100%` = fully open
- `30%` = 30% open and 70% closed

The integration sends `open` or `close`, waits for the calculated duration, then sends `stop`.

## Example

Source cover:

```text
cover.officesoversleft2
```

Travel time:

```text
35 seconds
```

If the smart cover is assumed to be at `100%` and you set it to `30%`, it will:

1. send `cover.close_cover` to the source cover
2. wait about `24.5 seconds`
3. send `cover.stop_cover`

Because:

```text
100% - 30% = 70%
70% of 35 seconds = 24.5 seconds
```

If it is assumed to be at `0%` and you set it to `30%`, it will:

1. send `cover.open_cover`
2. wait about `10.5 seconds`
3. send `cover.stop_cover`

Because:

```text
30% of 35 seconds = 10.5 seconds
```

## Features

- Creates a new virtual `cover` entity.
- Supports open, close, stop and set position.
- Works with the standard Home Assistant cover slider.
- Estimates position based on travel time.
- Restores the last assumed position after Home Assistant restart.
- Updates the cover position while moving so the UI feels responsive.
- Supports multiple smart covers, one config entry per source cover.
- Does not require YAML helpers, scripts, automations, timers or template covers.

## Important limitation

The position is estimated, not measured.

RTS/RFXtrx does not normally report exact cover position. If someone uses the physical remote or another integration outside RTS Smart Covers, the assumed position can become wrong.

Best practice:

- Control the cover through the new smart cover entity.
- Occasionally recalibrate by moving fully open or fully closed and setting the initial position/options accordingly.

## Installation via HACS custom repository

1. Push this repository to GitHub.
2. In Home Assistant, open HACS.
3. Open the menu with the three dots.
4. Select **Custom repositories**.
5. Add:

```text
https://github.com/haxxel1337/RTS-Smart-Covers
```

6. Select type:

```text
Integration
```

7. Install **RTS Smart Covers**.
8. Restart Home Assistant.

## Manual installation

Copy this folder:

```text
custom_components/rts_smart_covers
```

to your Home Assistant config folder:

```text
/config/custom_components/rts_smart_covers
```

Restart Home Assistant.

## Configuration

Go to:

```text
Settings -> Devices & Services -> Add Integration -> RTS Smart Covers
```

Fill in:

| Field | Example |
|---|---|
| Source cover | `cover.officesoversleft2` |
| Smart cover name | `Office Covers Left Smart` |
| Full travel time | `35` |
| Initial assumed position | `100` |

After setup, Home Assistant creates a new smart cover entity, for example:

```text
cover.office_covers_left_smart
```

Use this new smart cover in dashboards, automations and Mushroom cards.

## Testing from Developer Tools

Go to:

```text
Developer Tools -> Actions
```

Run:

```yaml
action: cover.set_cover_position
target:
  entity_id: cover.office_covers_left_smart
data:
  position: 30
```

Expected result from fully open with 35 second travel time:

```text
close for about 24.5 seconds, then stop
```

## Mushroom card example

```yaml
type: custom:mushroom-cover-card
entity: cover.office_covers_left_smart
name: Office Covers Left
show_position_control: true
show_buttons_control: true
fill_container: true
layout: vertical
```

## Branding

This repository includes a `brand` folder.

Place these files there:

```text
brand/logo.png
brand/icon.png
```

These are for your own project/repository branding. The integration itself does not require them to run.

## Development notes

Project domain:

```text
rts_smart_covers
```

Integration folder:

```text
custom_components/rts_smart_covers
```

GitHub repository:

```text
haxxel1337/RTS-Smart-Covers
```

## License

MIT
