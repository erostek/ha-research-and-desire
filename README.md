# Research and Desire Integration for Home Assistant

[![HACS Validation](https://github.com/erostek/ha-research-and-desire/actions/workflows/validate.yaml/badge.svg)](https://github.com/erostek/ha-research-and-desire/actions/workflows/validate.yaml)
[![Hassfest Validation](https://github.com/erostek/ha-research-and-desire/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/erostek/ha-research-and-desire/actions/workflows/hassfest.yaml)

Custom Home Assistant integration for [Research and Desire](https://researchanddesire.com/) devices. Supports the **Deepthroat Trainer (DTT)**, **Lockbox (LKBX)**, and **OSSM** — exposing session data, device status, and training metrics as Home Assistant entities.

## Features

- **Deepthroat Trainer** — 23 sensors + 1 event entity covering session results, training template details, and device info
- **Lockbox** — 10 sensors for lock status, active lock settings, break/shame/emergency configuration
- **OSSM** — 4 sensors (stub, ready for when a device is connected)
- **Event Entity** — fires `session_passed`, `session_failed`, or `session_completed` events for DTT sessions
- **Blueprints** — ready-to-import automation blueprints for common use cases
- **Cloud Polling** — polls the API every 60 seconds
- **No extra dependencies** — uses Home Assistant's built-in aiohttp session

## Requirements

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
4. Done — devices will appear automatically for each R&D product linked to your account

## Entities

### Deepthroat Trainer (DTT)

| Sensor | Description |
|--------|-------------|
| Latest Session Status | Passed / Failed / In Progress |
| Latest Session Grade | Average percent grade across segments |
| Latest Session Points | Total points from all segments |
| Latest Session Date | Session creation timestamp |
| Latest Session Segments | Number of segments in the session |
| Latest Session Duration | Total measured duration (seconds) |
| Session Distance | Total distance travelled across segments |
| Longest Deepthroat | Longest deepthroat measurement (ms) |
| Session Total Reps | Total reps measured across segments |
| Avg Stroke Length | Average stroke length (mm) |
| Avg Speed | Average measured speed |
| Active Template | Name of the active training program |
| Template Message | Motivational message from template |
| Template Tagline | Template tagline text |
| Toy Tagline | Toy-specific tagline |
| Hands-Free Mode | On / Off |
| Target Depth | Target depth (mm) |
| Target Window | Target window tolerance (mm) |
| Template Segments | Number of segments in the template |
| Software Version | Device firmware version |
| Last Seen | Last device connection time |
| Last Log | Last activity log timestamp |
| Serial Number | Device serial number |
| Best Segment Grade | Highest grade from session segments (%) |
| Worst Segment Grade | Lowest grade from session segments (%) |
| Max Speed | Maximum measured speed across segments |
| Passed Segments | Number of passed segments |
| Failed Segments | Number of failed segments |
| Segment Pass Rate | Percentage of segments passed (%) |

**Event entity:** `Session Completed` — fires `session_passed`, `session_failed`, or `session_completed` with data including `session_id`, `passed`, `total_points`, `average_grade`, `segment_count`, `created_at`.

### Lockbox (LKBX)

| Sensor | Description |
|--------|-------------|
| Lock Status | Locked / Unlocked |
| Last Seen | Last device connection time |
| MAC Address | Device Bluetooth MAC address |
| Active Lock | Name of active lock template, or "No active lock" |
| Lock Duration | Duration of the active lock (seconds) |
| Breaks Enabled | On / Off |
| Emergency Unlock | On / Off |
| Deepthroat Enabled | On / Off (DTT integration for lock time reduction) |
| Shame Enabled | On / Off |
| Test Lock | Yes / No |
| Break Regularity | Time between breaks (seconds) |
| Break Penalty | Time added for taking a break (seconds) |
| Max Break Duration | Maximum break length (seconds) |
| DTT Time Reduction | Lock time reduced per DTT session |
| Min Lock Duration | Minimum lock duration (seconds) |
| Max Lock Duration | Maximum lock duration (seconds) |
| Random Duration | Whether lock duration is randomized |
| Time Displayed | Whether remaining time is shown |
| Publicly Listed | Whether the lock is publicly listed |
| Template Count | Number of lock templates |
| Session Count | Number of lock sessions |

### OSSM

| Sensor | Description |
|--------|-------------|
| Session Count | Number of OSSM sessions |
| Pattern Count | Number of movement patterns |
| Firmware Version | Device firmware version |
| Last Seen | Last device connection time |

## Automation Blueprints

Ready-to-use automation blueprints — click to import directly into your Home Assistant:

### DTT Training Reminder

Send a notification if no training session has been completed by a specified time of day.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdaily_training_reminder.yaml)

### Session Completed Notification

Get notified with full session results (grade, points, segments) whenever a DTT session is completed.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fsession_completed_notification.yaml)

### Session Grade Light Feedback

Change a light color based on the session grade — green for passing grades, red for failing. Great for visual feedback in the training room.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fpoor_grade_light_feedback.yaml)

### Training Streak Tracker

Track consecutive training days using an HA counter helper. Sends a congratulations notification after each session with the streak count.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fsession_streak_tracker.yaml)

### Lockbox State Change Notification

Get notified whenever the Lockbox changes between Locked and Unlocked.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_state_notification.yaml)

### Lockbox Unlock Indicator Light

Automatically turn on a light or switch when the Lockbox is unlocked, and turn it off when locked again.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_break_light.yaml)

### DTT Reward — Scene on Pass

Activate a reward scene (mood lighting, music, etc.) when a DTT session is passed.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_reward_scene.yaml)

### DTT Punishment — Scene on Fail

Activate a punishment scene and send a shaming notification when a DTT session is failed.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_punishment_scene.yaml)

### DTT Tiered Grade Response

Run different scenes based on grade tiers — excellent, acceptable, or poor. Configurable thresholds for reward/neutral/punishment responses.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_grade_tiered_response.yaml)

### Missed Training Punishment

Activate a punishment scene and send a notification if no training is completed by the deadline.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_missed_training_punishment.yaml)

### Lockbox DTT Training Reward

Congratulate and notify when a DTT session is passed above a grade threshold. Pairs with Lockbox's built-in deepthroat time reduction feature.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_dtt_unlock_reward.yaml)

### Lockbox Controls Smart Devices

Turn off devices (TV, gaming, lights) when locked, turn them back on when unlocked. Enforce restricted access to privileges.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_lock_smart_devices.yaml)

### Lockbox Timed Unlock Reminder

Send warning and final notifications during Lockbox break time to enforce time limits.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_timed_unlock_reminder.yaml)

### Lockbox Shame Announcement

Announce lock/unlock status on a smart speaker via TTS. Use as a humiliation element.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_shame_announcement.yaml)

### DTT Personal Best Alert

Track your best session grade using an input_number helper. Get notified when you beat your personal best.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_personal_best_alert.yaml)

### DTT Training Buddy Notification

Notify a training partner or keyholder whenever a DTT session completes with full results.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_training_buddy_notify.yaml)

### DTT Reward Media Player

Play music or media on a media player when a session is passed. Stop media on failure.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_reward_media.yaml)

### DTT Weekly Training Summary

Every Sunday, receive a summary notification with your current session grade, points, reps, and training status.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_weekly_summary.yaml)

### DTT Failure Extends Lockbox

Notification when a failed DTT session results in added Lockbox time. Pairs with the Lockbox deepthroat time reduction feature.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Fdtt_fail_lockbox_extend.yaml)

### Lockbox Keyholder Activity Log

Send all Lockbox state changes to a keyholder's notification service with timestamps and active lock details.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_keyholder_log.yaml)

### Lockbox Controls Thermostat

Lower the thermostat when locked (punishment), raise it when unlocked (reward). Configurable temperatures.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_thermostat_control.yaml)

### Lockbox Camera Snapshot

Take a camera snapshot whenever the Lockbox state changes and send it via notification.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Ferostek%2Fha-research-and-desire%2Frefs%2Fheads%2Fmaster%2Fblueprints%2Fautomation%2Fresearch_and_desire%2Flockbox_camera_snapshot.yaml)

## Dashboard Samples

Ready-to-use dashboard YAML — copy into your Raw Configuration Editor:

| Dashboard | Description | YAML |
|-----------|-------------|------|
| **DTT Training** | Full training dashboard with gauges, segment analysis, template details | [`dashboards/dtt_training_dashboard.yaml`](dashboards/dtt_training_dashboard.yaml) |
| **Lockbox** | Lock status, settings, break config, device info | [`dashboards/lockbox_dashboard.yaml`](dashboards/lockbox_dashboard.yaml) |
| **R&D Overview** | Combined view of all R&D devices at a glance | [`dashboards/combined_overview.yaml`](dashboards/combined_overview.yaml) |

**How to import:** Settings > Dashboards > Add Dashboard > three dots > Raw configuration editor > paste YAML > Save

## API Documentation

This integration uses the [Research and Desire API](https://docs.researchanddesire.com/dashboard/api/introduction).

## License

MIT License — see [LICENSE](LICENSE).
