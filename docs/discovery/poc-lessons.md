# Lessons from the proof of concept

A single-TV LG webOS prototype ran daily in a real household. The code is not reused; the knowledge is.

## Rule semantics worth keeping
- Pure rules engine: `evaluate(now, state, settings) -> decision`, with an injectable clock and a fake TV for tests.
- A day with no windows is blocked all day; a window crossing midnight belongs to its starting day.
- 3 s debounce before acting, cooldown between warnings, cap on power-offs (3 in 5 minutes, then a 10 minute pause),
  ping-pong guard on the fallback channel/app.

## LG webOS quirks
- While watching live TV the foreground app is always `com.webos.app.livetv`; normalize it, otherwise channel rules never fire.
- A hard timeout is needed on websocket sends, not only on response waits. A dead peer (TV powered off abruptly,
  ARP black hole) can hang a send forever and freeze the supervision loop in a ghost "online" state.
- `connect()` raises a pairing error instead of returning false.
- In standby, some list queries return non-dict rows; filter them.
- `set_channel` needs the channel id, not the channel object.
- The native on-air title comes from `getChannelCurrentProgramInfo`, and only while live TV is the foreground app.
  webOS 4.5 does not expose a program list.
- App icons are served over HTTPS on port 3001 with a self-signed certificate; proxy them.
- With Quick Start+ the websocket stays alive while the screen is off: "online" does not mean "watching".

## Licensing
- Format `b64url(payload).b64url(signature)`, Ed25519, verified offline.
- The gate applies at runtime only. Configuration beyond the tier stays savable but inert.

## EPG
- Guide bodies may be gzip-compressed. Match channel names ignoring spaces and case.

## Home Assistant frontend gotchas
- Build the card DOM once; a periodic state update must not destroy an open dialog.
- Use `showModal()` for the top layer.
- Quote `off` in YAML (it parses as a boolean).
- Register frontend modules through the frontend data API available in the target HA version; test against the real minimum and latest versions.

## Mistakes not to repeat
- Vendoring the whole core inside the Home Assistant process and patching `sys.path`.
- Unpinned dependencies that collide with Home Assistant's own pins.
- Passing a PIN as service data (it lands in the event bus and traces).
- Two sources of truth for configuration (a settings file plus config-entry options).
- Absolute URL paths in the frontend (breaks Ingress).
- Testing against an older Home Assistant than the one used in production.
