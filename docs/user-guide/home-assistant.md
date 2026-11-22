# Home Assistant

TVBalance ships a custom integration that shows every TV as a device in Home Assistant, sends you events and lets
automations grant or take away TV time.

## Set up

### With the Add-on (recommended)

Install the TVBalance Add-on and start it. Home Assistant shows a **TVBalance** notification under
**Settings → Devices & services**: choose **Configure** and confirm. The Add-on creates and keeps the API token for
you; if you revoke it, restart the Add-on and Home Assistant picks up the new one.

### With a standalone Engine

1. In the TVBalance web UI, open **Settings → API tokens** and create a token with the **read** and **control**
   scopes. Add **admin** only if you want the `tvbalance.set_monitoring` service. The secret is shown once.
2. Install the integration with HACS (add `https://github.com/tvbalance/tvbalance-ha` as a custom repository,
   category Integration), or copy `custom_components/tvbalance` into your Home Assistant `config/custom_components`
   folder. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → TVBalance**. Enter the Engine URL and the token.

To use HTTPS, enter an `https://` address (port 8766 by default). When the certificate is not trusted yet, the setup
shows the fingerprint of the Engine's local certificate authority: compare it with **Settings → Secure connection**
in the TVBalance web UI and confirm. Home Assistant then accepts only that authority for this Engine. If the
authority changes (a new certificate was created), Home Assistant asks you to confirm it again. See https.md.

If the token is revoked or expires, Home Assistant asks you for a new one (a repair notice appears; choose
**Reconfigure**). Nothing else needs to be set up again.

## What you get per TV

| Entity | Meaning |
| --- | --- |
| Status (sensor) | `watching`, `standby`, `off`, `unreachable`, `needs_pairing` or `not_monitored` |
| App, Program (sensors) | What is on screen now. Input and Channel exist too, disabled by default |
| Watched today, Time left (sensors) | Minutes; Time left is unknown when the TV has no daily budget |
| Blocked (binary sensor) | On while enforcement blocks the TV; the `reason` attribute says why |
| Connected, Needs pairing (binary sensors) | Link health |
| Pause (button) | Pauses enforcement for 30 minutes. Safe for anyone to press |
| Activity (event entity) | Fires for each TVBalance event |

The Engine pushes changes live, so states update within a second. If the stream drops, Home Assistant reconnects on
its own and still polls every 30 seconds.

## Services (administrators only)

Anything that gives more TV time or changes enforcement is limited to Home Assistant administrators, so a child using
a dashboard cannot call it. Automations and scripts can. Every service takes a `device_id` (the TV).

| Service | Fields |
| --- | --- |
| `tvbalance.bonus` | `minutes` (1–240) |
| `tvbalance.allow` | `minutes` (1–1440) or `until_midnight` |
| `tvbalance.block` | `minutes` (1–1440) or `until_midnight` |
| `tvbalance.pause` | `minutes` (1–1440) |
| `tvbalance.clear_override` | none |
| `tvbalance.set_monitoring` | `enabled`; needs a token with the admin scope |

`allow` and `block` need exactly one of `minutes` or `until_midnight`. No PIN is ever part of a service call.

## Events

Each Engine event is also fired on the Home Assistant bus as `tvbalance_event`, with `device_id`, `tv_id`, `type`
and `payload`. Types: `time_warning` (`minutes_left`, `limit`), `blocked` (`reason`), `redirected` (`action`),
`powered_off`, `enforcement_paused`, `enforcement_unavailable` (`reason`), `tv_unreachable`, `tv_reachable`,
`pairing_lost`, `tv_paired`.

## Blueprints

Under `blueprints/automation/tvbalance/`; copy them to `config/blueprints/automation/tvbalance/`.

- **warning_light**: flash a light when a TV has N minutes or fewer left.
- **notify_parent**: send a notification for the events you choose.
- **button_bonus**: grant bonus minutes when a physical button is pressed.
