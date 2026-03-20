# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration for Research and Desire (R&D) Deepthroat Trainer (DTT) devices. Polls the R&D cloud API for session data, device info, and training templates, exposing them as HA sensor and event entities. Requires an R&D Ultra subscription API key.

## Development

There is no build system, test suite, or linting configuration. The integration is pure Python with no external dependencies (uses HA's built-in `aiohttp`).

**Local development:** Copy `custom_components/research_and_desire/` into your HA `config/custom_components/` directory and restart Home Assistant.

**CI:** Two GitHub Actions workflows validate the manifest (`hassfest`) and HACS compatibility (`validate`).

## Architecture

All code lives in `custom_components/research_and_desire/`.

**Data flow:** `config_flow.py` (validates API key) → `api.py` (HTTP client) → `coordinator.py` (polls every 60s) → `sensor.py` + `event.py` (entities)

**Key design decisions:**
- **Sequential API calls** in the coordinator (not parallel) to avoid rate limiting. This was an intentional fix for flapping issues.
- **Flexible segment extraction** (`_get_segments` in `sensor.py`) tries multiple key names and falls back to heuristic list detection, because the API response format varies.
- **Session completion detection** compares session IDs between polls; a changed ID triggers event firing.
- **API response envelope:** All responses use `{"ok": true, "data": {...}}` wrapper. The client's `_extract_list()` tries multiple keys (`items`, `devices`, `sessions`, etc.) for list responses.

**Entity pattern:** Sensors use dataclass-based descriptions (`ResearchAndDesireSensorDescription`) with `value_fn`/`attr_fn` callbacks that extract values from the coordinator's `ResearchAndDesireData` dataclass.

## API

Base URL: `https://dashboard.researchanddesire.com/api/v1`
Auth: Bearer token in `Authorization` header

| Endpoint | Purpose |
|----------|---------|
| `GET /dtt` | List devices |
| `GET /dtt/sessions/latest` | Latest session summary |
| `GET /dtt/sessions/{id}` | Full session with segments |
| `GET /dtt/templates/active` | Active training template |

## Platforms

- **sensor** — 10 entities: session status/grade/points/date/segments/duration, device version/last seen, active template, target depth
- **event** — Fires `session_passed`/`session_failed`/`session_completed` on new session detection
