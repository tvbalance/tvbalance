# TVBalance

**Healthy screen-time rules for your family's smart TV.**

TVBalance is a local-first parental control for smart TVs. It enforces viewing schedules, daily time
budgets and app/input/channel rules on the TV itself, and plugs natively into Home Assistant.

> **Status: pre-alpha (discovery and architecture).** Nothing here is usable yet.

## Vision

- **Multi-brand:** LG webOS, Roku TV, Google/Android TV and Samsung Tizen through a plugin adapter SDK.
- **Home Assistant first:** an Add-on with Ingress plus a thin HACS integration exposing native entities,
  services and events for automations. Also runs standalone in Docker.
- **Local-first:** no cloud account, no telemetry by default, no subscription.
- **Open core:** the core, the adapters and the Home Assistant integration are Apache-2.0.
  A one-time Pro license (offline, signed) unlocks advanced features.
- **Zero friction:** automatic TV discovery, guided pairing, automatic language and country detection.

## Repository layout

| Path | Purpose |
|---|---|
| `engine/` | The TVBalance Engine (Python, asyncio, FastAPI) |
| `adapters/` | One package per TV brand |
| `client/` | Async API client used by the Home Assistant integration |
| `ha/` | Home Assistant custom integration (HACS) |
| `addon/` | Home Assistant Add-on |
| `web/` | Web UI and PWA (React, TypeScript, Vite) |
| `docs/` | Product spec, architecture decisions, plans, user guide |

## Documentation

- [Product specification](docs/product/spec.md)
- [Architecture decision records](docs/architecture/adr/)
- [Discovery notes](docs/discovery/)

## License

Apache License 2.0. See [LICENSE](LICENSE).
