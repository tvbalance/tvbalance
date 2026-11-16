# Domain rules reference

The rules engine lives in `engine/src/tvbalance/domain/` and is pure: no I/O and no clock. Callers pass
`now` as a timezone-aware datetime in the household's zone.

## Schedule
- A day without windows is blocked all day. `special_days` (per date) replaces the weekday rule.
- A window with `start > end` crosses midnight and belongs to the day it starts on; `start == end` means 24 hours.
  Overlapping or adjacent windows (also across midnight) merge into one span.
- Spans are computed in UTC, so a DST change shortens or lengthens a window by the real elapsed time.

## Evaluation order (`evaluate`)
1. TV not on (standby/off): `Allow`.
2. Most recent active override. A block override: `Block(OVERRIDE)`, even for always-allowed content.
3. Always-allowed app, input or channel: `Allow` (no limits, no budget use).
4. Unless an allow override is active: outside every window `Block(OUTSIDE_WINDOW)`, budget spent `Block(BUDGET_EXHAUSTED)`.
5. Blocked app/input/channel, or app outside the allow list: `Block(APP|INPUT|CHANNEL_BLOCKED)`.
6. Otherwise `Warn(minutes, limit)` when the nearest limit (window end, budget, override end) is within the
   largest warning threshold; minutes round up. Else `Allow`.

An allow override lifts time limits only; content blocks still apply.
The default `Policy()` has an empty schedule and therefore blocks everything: the supervisor only enforces
once a household has configured rules.

## Budget
`accrue` adds elapsed time while the TV is on with non-exempt content. A new local day starts from zero
(bonus minutes included); time before local midnight is never billed to the new day; one gap is capped at 120 s.

## Enforcement (`step`)
- Debounce (3 s) before the first action of an episode; an episode ends when the decision is `Allow`/`Warn`
  or the TV is not on.
- First action: on-screen message. Blocked content is also redirected immediately (fallback if usable, else home).
- After the grace period (15 s): time limits redirect to the fallback only if it is always-allowed, otherwise
  power off. One redirect per episode; a further grace period precedes power-off.
- At most 3 power-offs in 5 minutes, then enforcement pauses for 10 minutes (`EnforcementPaused`).
- When the TV cannot power off, `EnforcementUnavailable` is reported once and the message repeats every 60 s.
- Each warning threshold fires once per day; a bonus that lifts the remaining time re-arms lower thresholds.
  `Allow` while the TV is on clears fired thresholds.

Messages are named (`MessageKind`), never rendered here; localized text is added by the supervisor/API layers.
`validate_policy` reports configuration problems (blocked fallback, conflicting lists, bad thresholds,
overlapping windows) without rejecting the configuration.

## Supervision (`tvbalance.app`)

One `TvWorker` per enabled TV whose adapter is installed, started by the `Supervisor` with the app.

- Tick (every 2 s, or at once on a push from the adapter): observe, bill the time since the last tick
  (`accrue`, capped at 120 s), `evaluate`, `step`, persist the enforcement state, then run the actions with
  localized texts and publish the events. A TV without a policy is only observed.
- Time while the TV is unreachable is never billed. Failed commands are logged and do not stop the others;
  an `execute` timeout drops the session.
- Connection errors back off from 2 s to 60 s. A refused key (`TVPairingError`) or unreadable stored
  credentials report `pairing_lost` and park the worker until `Supervisor.refresh`, so a rejected key never
  makes the TV show a pairing prompt in a loop.
- Events (stored in the event log and fanned out by `EventBus` to bounded queues): `time_warning`, `blocked`,
  `redirected`, `powered_off`, `enforcement_paused`, `enforcement_unavailable`, plus `tv_unreachable` (once per
  outage, only if the TV was on), `tv_reachable` and `pairing_lost`.
- Texts live in `locales/{en,it,de,fr,es}.json`; the `language` setting picks one (English as fallback) and the
  `timezone` setting defines the household day (the system zone when unset or invalid).
