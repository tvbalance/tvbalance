# TVBalance

Healthy screen-time rules for your family's smart TV.

## Installation

1. In Home Assistant, open **Settings → Add-ons → Add-on Store → ⋮ → Repositories**.
2. Add `https://github.com/tvbalance/tvbalance`.
3. Install **TVBalance**, start it and open the **TVBalance** panel in the sidebar.
4. Follow the on-screen setup: create the administrator password, then add your first TV.

## Home Assistant integration

When the Add-on starts it announces itself to Home Assistant. A **TVBalance** notification appears under
**Settings → Devices & services**: choose **Configure** and confirm. No address or token has to be typed.

The Add-on creates an API token named "Home Assistant (Add-on)" with the read and control scopes and keeps it
across restarts. If you revoke it in **Settings → API tokens**, restart the Add-on: it creates a new one and Home
Assistant picks it up on its own.

## Network

The Add-on uses the host network so it can discover TVs and send Wake-on-LAN packets.
The Engine listens on port 8765 (HTTP, also used by Ingress) and on port 8766 (HTTPS).

## HTTPS

By default the Add-on serves HTTPS on port 8766 with a certificate from its own local authority, renewed by
itself. Open **Settings → Secure connection** in the TVBalance panel to download the certificate, install it on
your devices and compare its fingerprint. Web Push notifications need this secure address.

Options:

- **HTTPS**: `auto` (default) or `off`.
- **Certificate file** and **Key file**: use your own certificate instead. The names are relative to Home
  Assistant's `/ssl` folder, for example `fullchain.pem` and `privkey.pem`.
- **Extra names**: more names for the automatic certificate. Only local names and private addresses are
  accepted.

The Home Assistant integration keeps working over HTTP inside the host. If you point it at an `https://` address
instead, it asks you to confirm the certificate fingerprint once.

## Data

All data lives in the Add-on's `/data` folder and is included in Home Assistant backups:

- `tvbalance.db`: your TVs, rules, usage history and events.
- `secret.key`: the key that protects the stored TV credentials. Keep it together with the database: if
  it is lost, the data stays but every TV has to be paired again.

## Support

Open an issue at https://github.com/tvbalance/tvbalance/issues and attach the diagnostics download.
