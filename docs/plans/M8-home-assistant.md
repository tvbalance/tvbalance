# M8: Full Home Assistant integration

Status: done.

## Goal
Spec F10: every TV becomes a Home Assistant device with entities, a harmless Pause button, admin-only services,
events for automations, and ready-made blueprints.

## Product decisions
- Entities are read-only, plus a **Pause** button (30 minutes). Anything that grants more TV time or changes
  enforcement is a service that needs Home Assistant admin permission: `bonus`, `allow`, `block`, `pause`,
  `clear_override`, `set_monitoring`. Automations and blueprints can still call them.
- No PIN ever travels in service data. `set_monitoring` needs an API token with the admin scope; the other calls need
  read and control.
- A token that expires or is revoked starts the Home Assistant reauth flow.
- Out of scope: Supervisor discovery (M9), active profile (Pro, M16), calendar blueprint (M16).

## Client (0.1.0)
`TvStatus.input_id/channel_id/program_title`, `Decision.limit`, `me()`, `update_tv()`.

## Integration
- `coordinator.py`: polls `tvs()` every 30 s; a background task consumes the WebSocket with backoff (1 s to 60 s).
  `status` messages patch the TV in place; other events fire the bus event `tvbalance_event` and feed the event entity.
- One device per TV (`(tvbalance, tv_id)`); TVs added later get entities, removed TVs lose their device.
- Platforms: `sensor` (status, app, input, channel, program, watched today, time left), `binary_sensor` (blocked,
  connected, needs pairing), `button` (pause), `event` (activity).
- Services in `services.yaml`, registered with `async_register_admin_service`, addressed by `device_id`.
- Config flow: reauth. Translations in five languages, with a parity test.
- Blueprints: `warning_light`, `notify_parent`, `button_bonus`.

## Tests
Setup states for each TV condition, reauth, event stream (status patch, bus event, reconnect, auth failure), TV
added/removed, Pause button, services (body, admin check, no-user context, unknown device, 403), blueprint
validation, translation parity. Client: new fields, `me()`, `update_tv()` against a real engine.

## Commit sequence
1. Plan (this document).
2. Client: full status fields, `me()`, `update_tv()`, 0.1.0.
3. Coordinator, devices, sensors, binary sensors, reauth.
4. Live event stream and event entity.
5. Pause button and admin-only services.
6. Blueprints.
7. User guide and plan status.
