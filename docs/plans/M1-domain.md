# M1 — Domain: schedules, budget, `evaluate`, enforcement

## Goal
A pure rules engine (no I/O, no internal clock) that M3 (supervisor), M5 (API) and M8 (Home Assistant) build on.
Behaviour is specified here and tested first, including property-based invariants.

## Product decisions
- An "allow for N minutes" override bypasses time limits only (windows and budget); content blocks stay in force.
  A "block" override (pause, dinner) bypasses everything. The most recently created active override wins.
- The Free daily budget counts all time the TV is on and resets at local midnight. *Always-allowed* content
  (apps, inputs, channels, e.g. a parents' news channel) is never subject to windows or budget and does not consume it.
- Escalation ladder:
  - Time limits (outside window, budget exhausted): message, then after a grace period redirect to the fallback
    target if it is always allowed and the TV supports it, otherwise power off.
  - Blocked content inside a window: message plus immediate redirect (fallback if allowed, otherwise home);
    power off only if the viewer insists after the grace period.
  - Safeguards from the prototype: 3 s debounce, at most 3 power-offs in 5 minutes then a 10 minute pause,
    one redirect per episode, each warning threshold fires once per day.

## Model changes (`domain/models.py`)
- `TimeWindow`: `start > end` crosses midnight and belongs to its starting day; `start == end` means 24 h.
- `Schedule.special_days`: per-date windows replacing the weekday rule (empty tuple = blocked).
- Targets `AppTarget`, `InputTarget`, `ChannelTarget`, `HomeTarget`; `EscalationSettings`.
- `Policy`: always-allowed sets, `fallback`, `escalation`. `Usage`: `day`, `watched_seconds`, `bonus_minutes`.
- `Override.created_at`; `Warn.limit`; `ShowMessage(kind, minutes_left)` (the domain never renders text;
  localized strings arrive with M3/M5); domain events for the supervisor.

## New modules (`domain/`)
`schedule.py` (allowed spans, midnight and DST aware), `budget.py` (remaining time, accrual),
`rules.py` (`evaluate`, `plan_actions`), `enforcement.py` (state machine `step`), `validation.py` (`validate_policy`).

## Tests
Unit tests per module plus `hypothesis` invariants (power not on is always allowed; active block override always
blocks; outside every window is never allowed; budget monotonicity; no negative minutes around DST;
`plan_actions` only uses available capabilities; power-off cap and one redirect per episode).
Domain branch coverage is enforced at 95 % in CI.

## Commit sequence
Plan, schedule spans, usage and budget, `evaluate`, planning and enforcement, validation,
property tests with coverage gate, docs (rules reference and spec update).
