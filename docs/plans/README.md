# Implementation plans

Each module below gets its own plan file in this folder (`M<n>-<slug>.md`) before any code is written.
A plan lists the goal, the files touched, the tests to write first, and a verification checklist.
Modules are implemented one at a time, test first, with small commits.

## Definition of done (every module)

- Tests written first and passing; `ruff`, `mypy` and the web linters clean.
- Public behavior documented (user guide or developer docs) and translated strings present in all five locales.
- `engine/openapi.json` and the generated web API types regenerated when the API changes.
- CI green.

## Modules

| # | Module | Depends on |
|---|---|---|
| M1 | Domain: schedules, budget, `evaluate`, `plan_actions` (done, see M1-domain.md) | skeleton |
| M2 | Persistence, configuration, migrations (done, see M2-persistence.md) | skeleton |
| M3 | Supervisor, enforcement loop, event bus (done, see M3-supervisor.md) | M1, M2 |
| M4 | LG webOS adapter (done and verified on hardware, see M4-webos.md) | skeleton |
| M5 | API v1, authentication, WebSocket events (done, see M5-api.md and architecture/api.md) | M2, M3 |
| M6 | Web UI: onboarding, rules, dashboard, settings (done, see M6-web.md and user-guide/web-ui.md) | M5 |
| M7 | Discovery and guided pairing wizard (done, see M7-pairing.md and architecture/api.md) | M4, M5 |
| M8 | Full Home Assistant integration: entities, admin-only services, events, blueprints (done, see M8-home-assistant.md) | M5 |
| M9 | Add-on release, Supervisor discovery, ghcr/PyPI/HACS publishing (done, see M9-addon-release.md and operations/release.md) | M5, M8 |
| M10 | Web Push notifications (done, see M10-web-push.md and user-guide/web-ui.md) | M5, M6 |
| M11 | Licensing and entitlements (done, see M11-licensing.md, user-guide/pro.md and operations/licensing.md) | M2 |
| M12 | Roku adapter (feasibility spike first) | skeleton |
| M13 | Google/Android TV adapter (feasibility spike first) | skeleton |
| M14 | Samsung Tizen adapter (feasibility spike first) | skeleton |
| M15 | EPG catalog and channel matching (Pro, private repository) | M11 |
| M16 | Profiles and calendar, advanced budgets, reports (Pro; done, see M16-pro-features.md and user-guide/pro.md) | M1, M11 |
| M17 | Documentation site and user guide in five languages (done, see M17-docs-site.md) | any |
| M18 | HTTPS on the LAN with a locally managed certificate (done, see M18-https-lan.md and user-guide/https.md) | M5, M6, M8 |

## Decisions that deviate from the first skeleton plan

- The shared image uses `python:3.13-slim` instead of the Home Assistant base images, so the same image serves
  the Add-on and standalone Docker, for amd64 and arm64.
- The Add-on announces itself through Supervisor `discovery` (M9); the integration offers a confirm step.
- shadcn/ui components are added per need during M6; the skeleton only ships Tailwind and a class-name helper.
- TypeScript is pinned to 5.9 because `openapi-typescript` does not support 6 or 7 yet.
- Home Assistant tests need a C toolchain on Windows, so locally they run in a Linux container
  (`python:3.13` and `python:3.14`); CI runs them natively.
- The Home Assistant integration lives in `ha/custom_components/tvbalance`; HACS needs it at the root of a
  dedicated repository, so releases mirror it (see M9).
- On-screen texts are named by `MessageKind` in the domain; localized rendering is part of M3/M5.
