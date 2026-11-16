# M3: Supervisor, enforcement loop, event bus

## Goal
Make the pure domain (M1), the storage (M2) and the adapters (M4) work together. For every paired TV a worker
observes the TV through `TVSession` (hard timeouts), accrues the daily usage, evaluates the rules, advances the
enforcement state machine, executes the planned actions with localized on-screen texts and publishes events.
The loop never blocks, reconnects by itself and applies a rule within about 5 s. The API (M5) and the Home
Assistant integration (M8) build on the supervisor's status and event bus.

## Product decisions
- The enforcement state (debounce, fired warnings, power-off counter, pause) is **persisted** (migration `0002`)
  and survives restarts, for example during an Add-on update.
- On-screen messages are **localized in M3** in English, Italian, German, French and Spanish. The language comes
  from the `language` setting (default `en`).
- The milestone ends with a supervised run on the real LG TV.

## Events (`app/events.py`)
- `to_record(event)` maps each domain event to a snake_case type and a JSON payload: `time_warning`, `blocked`,
  `redirected`, `powered_off`, `enforcement_paused`, `enforcement_unavailable`.
- Supervisor events: `tv_unreachable` (the connection drops while the last observation was ON, once per outage, so
  a normal standby is silent), `tv_reachable` and `pairing_lost`. The names follow spec F10.
- `EventBus.publish` appends to the stored event log and then fans out to subscribers. `subscribe()` yields a
  bounded queue (100); a slow subscriber loses its oldest events and never blocks the publisher. A failing log
  write is logged and the fan-out still happens.

## On-screen texts (`app/messages.py`, `locales/*.json`)
Keys are the `MessageKind` values, with a `{minutes}` placeholder and a variant without minutes, like
`sdk/messages.default_text`. `localize(action, language)` fills `ShowMessage.text`, falls back to English for an
unknown language and leaves other actions untouched. The JSON files ship as package data. A test checks that the
five locales have the same keys and placeholders.

## Enforcement state persistence
- Migration `0002_enforcement_state`: `enforcement_state(tv_id PK, FK to tvs with cascade, state JSON, updated_at)`.
- `infra/db/state_codec.py`: versioned `encode_state` / `decode_state`. An unreadable document yields a default
  `EnforcementState` and a log entry.
- Port `EnforcementStateStore` (`load` returns the default when absent, `save` upserts), exposed as
  `Storage.enforcement`. The worker saves only when the state changed.

## Worker (`app/worker.py`)
One `TvWorker` per enabled TV; `run()` stops only when cancelled.
- **Connection:** the adapter comes from `plugin.factory` and is used through `TVSession`. A `TVPairingError` emits
  `pairing_lost` and the worker waits for a `refresh` (retrying with a rejected key would pop a prompt on the TV).
  Other `TVError`s close the session and retry with exponential backoff (2 to 60 s). `needs_pairing` records emit
  `pairing_lost` without connecting.
- **Push:** with `Capability.PUSH_UPDATES` and `SupportsPush`, a change wakes the tick at once; otherwise the worker
  polls every `tick_interval` (2 s).
- **Tick:** observe; reload TV, policy, usage and active overrides; `accrue`; `evaluate`; `step`; execute the
  localized actions (a failing action is logged and does not stop the others); publish events; save the state if
  it changed; refresh the status. Time while the TV was unreachable is never billed. A TV without a policy is only
  observed. The household time zone comes from the `timezone` setting, else the system zone.
- An unexpected failure in a tick is logged and the loop resumes after `tick_interval`.

## Supervisor (`app/supervisor.py`)
`Supervisor(storage, plugins, bus, clock, settings)` with `start()`, `refresh(tv_id | None)`, `status(tv_id)`,
`statuses()` and `stop()`. `TvStatus` carries connection and pairing flags, the last observation and decision,
watched and remaining seconds. A TV whose adapter is not installed is logged and skipped. A worker that exits
unexpectedly is logged and restarted.

## Wiring
The `create_app` lifespan opens the storage, the bus and the supervisor, exposes them as `app.state.supervisor` and
`app.state.events`, and stops them in reverse order. Plugins and the clock can be injected for tests.

## Out of scope
HTTP and WebSocket endpoints for status and events (M5), the pairing flow (M7), Home Assistant entities (M8).

## Tests
Unit tests with `FakeTV` and a controllable clock: block, message and power-off; usage accrual; no policy;
unreachable and back with events; a hanging `observe`; lost pairing; push wake-up; state resumed after a restart;
supervisor start, refresh, stop, missing adapter and a crashing worker; lifespan wiring. Migration and codec
round-trip tests with `hypothesis`.

## Commit sequence
Plan; events and bus; localized texts; state codec, migration and store; worker; supervisor and wiring;
documentation and coverage gate.

## Hardware check
A script in the scratchpad (not in the repo) pairs the stored TV, creates a test policy (blocked app, Italian)
and runs the supervisor for a few minutes while the user confirms what the TV shows: message and redirect to Home,
then a block override ending in power off. Host and key are never printed.
