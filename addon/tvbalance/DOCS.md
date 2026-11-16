# TVBalance

Healthy screen-time rules for your family's smart TV.

> **Pre-alpha.** This Add-on starts the TVBalance Engine and shows its status page. Rules, pairing
> and the Home Assistant entities arrive in later releases.

## Installation

1. In Home Assistant, open **Settings → Add-ons → Add-on Store → ⋮ → Repositories**.
2. Add `https://github.com/tvbalance/tvbalance`.
3. Install **TVBalance**, start it and open the **TVBalance** panel in the sidebar.

## Network

The Add-on uses the host network so it can discover TVs and send Wake-on-LAN packets.
The Engine listens on port 8765 (also used by Ingress).

## Data

All data lives in the Add-on's `/data` folder and is included in Home Assistant backups.

## Support

Open an issue at https://github.com/tvbalance/tvbalance/issues and attach the diagnostics download.
