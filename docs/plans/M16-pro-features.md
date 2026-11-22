# M16: Profiles and calendar, advanced budgets, reports (Pro)

Status: in progress.

## Goal
Spec F3, F6, F9 and F10: give the Pro license real features on top of the `Entitlements` port from M11.
Configuration is always savable; the gate applies only at runtime. Without Pro, profiles and the calendar are
ignored (the rule assigned to the TV applies), advanced budgets fall back to the base daily budget, rollover is
zero and the history stays at seven days. Nothing is lost when a license ends.

## Product decisions
- A profile is an existing rule set (`policies`), not a new kind of rule.
- An active profile applies to the whole household, minus the TVs excluded when it is activated (for example the
  parents' TV). There are no per-child profiles (spec, out of scope for v1).
- Precedence: a manual activation in force, then a calendar entry by dates, then a weekly calendar entry, then
  the rule assigned to the TV.
- "Categories" for budgets are groups of apps the parent defines, because adapters expose no categories.
- Open/closed boundary (ADR 0006): the code stays in this repository, isolated in its own modules behind
  `Entitlements`, so it can still be moved into a closed package before the repository is made public.

## M16a: profiles and calendar
- `domain/profiles.py`: `ProfileActivation`, `CalendarEntry`, `resolve_profile`. Pure and tested around time zones
  and midnight.
- Migration `0005` (`profile_activations`, `calendar_entries`), `ProfileStore` port, repository.
- `app/profiles.py` `ProfileService`; the worker picks the effective policy through it when Pro is active.
  Events `profile_started` and `profile_ended`. `TvStatus.active_profile`.
- API: `/profiles/active` (control scope) and `/calendar` (admin).
- Web: activate as profile, active-profile banner, calendar editor. Client, Home Assistant sensor, services and a
  calendar blueprint.

## M16b: advanced budgets
- `content_usage` table (migration `0006`): seconds per app, input or channel per day, accrued next to `accrue`.
- `Policy` gains per-weekday budgets, app-group budgets and a rollover cap; the policy document moves to version 2
  and still reads version 1.
- `remaining_seconds` and `evaluate` use them; new block reason for an exhausted app group.
- Editor tab, messages and notifications for the new reason.

## M16c: reports
- History beyond seven days (up to 366) and per-content usage (Pro).
- Weekly report computed from usage and events, published on Monday morning in the household's zone as the
  `weekly_report` event (Web Push and Home Assistant).
- Activity page with a selectable range, per-app chart and the weekly view.

## Out of scope
Per-child profiles, EPG and content blocking by title (M15), merchant automation.
