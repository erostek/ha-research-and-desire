# Research and Desire Integration for Home Assistant

[![HACS Validation](https://github.com/erostek/ha-research-and-desire/actions/workflows/validate.yaml/badge.svg)](https://github.com/erostek/ha-research-and-desire/actions/workflows/validate.yaml)
[![Hassfest Validation](https://github.com/erostek/ha-research-and-desire/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/erostek/ha-research-and-desire/actions/workflows/hassfest.yaml)

Custom Home Assistant integration for [Research and Desire](https://researchanddesire.com/) devices. Pulls Deepthroat Trainer (DTT) session data from the Research and Desire cloud API and exposes it as Home Assistant entities.

## Features

- **10 Sensors** — session status, grade, points, duration, segments, date, device software version, device last seen, active template, target depth
- **Event Entity** — fires `session_passed`, `session_failed`, or `session_completed` events for use in automations
- **Cloud Polling** — polls the API every 60 seconds with parallel endpoint fetching
- **No extra dependencies** — uses Home Assistant's built-in aiohttp session

## Requirements

- Home Assistant 2024.4.0 or newer
- Research and Desire account with **Ultra** subscription (required for API access)
- API key from [R&D Dashboard](https://dashboard.researchanddesire.com/) (Settings > API Keys)

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=erostek&repository=ha-research-and-desire&category=integration)

Or manually:

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) > **Custom repositories**
3. Add `https://github.com/erostek/ha-research-and-desire` with category **Integration**
4. Search for "Research and Desire" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/research_and_desire/` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=research_and_desire)

Or manually:

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Research and Desire**
3. Enter your API key
4. Done — entities will appear under the **DTT Trainer** device

## Entities

### Sensors

| Sensor | Description | Device Class |
|--------|-------------|-------------|
| Latest Session Status | Passed / Failed / In Progress | — |
| Latest Session Grade | Average percent grade across segments | — (%) |
| Latest Session Points | Total points from all segments | Total Increasing |
| Latest Session Date | Session creation timestamp | Timestamp |
| Latest Session Segments | Number of segments | — |
| Latest Session Duration | Total measured duration | Duration (s) |
| Device Software Version | DTT firmware version | — |
| Device Last Seen | Last device connection time | Timestamp |
| Active Template | Name of active training program | — |
| Target Depth | Target depth from active template | — (mm) |

### Events

| Entity | Event Types | Description |
|--------|-------------|-------------|
| Session Completed | `session_passed`, `session_failed`, `session_completed` | Fires when a new session is detected |

Event data includes: `session_id`, `passed`, `total_points`, `average_grade`, `segment_count`, `created_at`.

## Automation Example

Trigger an automation when a session is passed:

```yaml
automation:
  - alias: "DTT Session Passed"
    trigger:
      - platform: state
        entity_id: event.dtt_trainer_session_completed
        attribute: event_type
        to: "session_passed"
    action:
      - service: notify.mobile_app
        data:
          title: "DTT Session Passed!"
          message: >
            Score: {{ trigger.to_state.attributes.total_points }} points,
            Grade: {{ trigger.to_state.attributes.average_grade }}%
```

## API Documentation

This integration uses the [Research and Desire API](https://docs.researchanddesire.com/dashboard/api/introduction).

## License

MIT License — see [LICENSE](LICENSE).
