# M4 — LG webOS adapter

## Goal
Replace the `adapters/webos` stub with a real adapter built on `aiowebostv`. It is the first brand and the only
one verifiable on real hardware. A simulator makes it testable in CI without a TV.

## Library spike (aiowebostv 1.1.0)
- State is cached in `client.tv_state` (`WebOsTvState`: `power_state`, `current_app_id`, `apps`, `inputs`,
  `current_channel`, `channels`, `is_on`, `is_screen_on`). Changes are pushed to callbacks added with
  `register_state_update_callback`.
- `connect()` returns `bool` and raises `WebOsTvPairError` when pairing is needed; the exception tree is
  `WebOsTvError` > `WebOsTvPairError` / `WebOsTvCommandError` (> timeout, response type, service not found).
- `set_channel(channel)` takes the channel **id**. `button(name)` goes through a separate input socket.
  `power_off()` is a no-op when the TV is already off. `send_message(message)` shows the toast.
- `WebOsClient(host, client_key=None, connect_timeout=2, heartbeat=5, client_session=None)`.
- The library applies its own timeouts to some calls only; the adapter adds none, `TVSession` wraps every call.

## Design
- `observe()` always issues a lightweight request (power state) in addition to reading the cache, so a dead
  peer fails instead of looking online.
- Power: `Active` and `Screen Saver` map to ON; `Screen Off`, `Active Standby` and `Suspend` map to STANDBY
  (Quick Start+ keeps the socket alive while the screen is off); a closed socket maps to OFF.
- Foreground: `com.webos.app.livetv` becomes `foreground_app=None` plus the current channel; HDMI apps become an
  `input_id`; anything else is the app id. Non-dict rows in list responses are discarded.
- Library and socket errors become `TVError`; pairing failures become `TVPairingError`.
- `WAKE` is not declared until the domain has a wake action.

## Shared changes
- `ShowMessage.text` (optional) plus `sdk/messages.default_text` as the English fallback.
- Optional `SupportsPush` port (`on_change(callback) -> unsubscribe`) for the supervisor.
- Entry point group `tvbalance.adapter_harnesses`: adapters expose a simulated TV to the contract suite.

## Testing
- An in-process SSAP websocket simulator (`tvbalance_adapter_webos.testing`) with knobs for TV state, non-dict
  rows, abrupt close and a mute peer.
- Unit tests for mapping, adapter, pairing and discovery; the contract suite runs against the simulator.
- Hardware tests are excluded by default. `hardware` is read-only; `hardware_actions` runs only in a manual
  session. Host and key come from `TVBALANCE_WEBOS_HOST` / `TVBALANCE_WEBOS_KEY`, never from the repo.

## Commit sequence
Plan; sdk changes; simulator; mapping; adapter; pairing; discovery; contract + hardware markers; user guide.
