# Install TVBalance

TVBalance runs on a small always-on computer in your home: the machine that runs Home Assistant, a NAS or a
Raspberry Pi. It needs to be on the same network as your TV. Pick one of the two ways below.

## As a Home Assistant Add-on (recommended)

This works with Home Assistant OS and Supervised installs, on amd64 and aarch64.

1. In Home Assistant, open **Settings → Add-ons → Add-on Store → ⋮ → Repositories**.
2. Add `https://github.com/tvbalance/tvbalance`.
3. Install **TVBalance**, start it and open the **TVBalance** panel in the sidebar.
4. Follow the on-screen setup. See [Getting started](getting-started.md).

When the Add-on starts it announces itself to Home Assistant. A **TVBalance** notification appears under
**Settings → Devices & services**: choose **Configure** and confirm. No address or token has to be typed. More
details are in [Home Assistant](home-assistant.md).

The Add-on uses the host network, so it can find TVs and wake them up. All of its data lives in the Add-on's
`/data` folder and is part of Home Assistant backups.

## With Docker

One multi-architecture image (amd64 and arm64) serves everything else:

```
docker run -d --name tvbalance --restart unless-stopped \
  --network host \
  -v tvbalance-data:/data \
  ghcr.io/tvbalance/tvbalance:latest
```

Then open `http://<address-of-the-machine>:8765` in a browser.

- **Host network.** TV discovery and Wake-on-LAN need it, and it only works this way on Linux. On Docker Desktop
  (Windows and macOS) use `-p 8765:8765 -p 8766:8766` instead and add your TV by its address, since it cannot be
  found automatically.
- **The data volume.** `/data` holds `tvbalance.db` (your TVs, rules, usage history and events) and `secret.key`
  (the key that protects the stored TV credentials). Keep both together and back them up together. If the key is
  lost, the data stays but every TV has to be paired again.
- **Updates.** Pull the new image and recreate the container. The database is upgraded on start.

### Settings

The Engine reads its settings from environment variables. The defaults are right for most homes.

| Variable | Default | Meaning |
| --- | --- | --- |
| `TVBALANCE_DATA_DIR` | `/data` | Where the database and the key live |
| `TVBALANCE_PORT` | `8765` | HTTP port |
| `TVBALANCE_HTTPS_PORT` | `8766` | HTTPS port |
| `TVBALANCE_TLS` | `auto` | `auto` for the built-in local certificate authority, `off` to turn HTTPS off |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | unset | Your own certificate and key (set both) |
| `TVBALANCE_TLS_NAMES` | unset | Extra local names for the automatic certificate |

HTTPS is explained in [HTTPS on your network](https.md).

### Home Assistant with a standalone Engine

Create an API token in the web app and install the integration with HACS. The steps are in
[Home Assistant](home-assistant.md#with-a-standalone-engine).

## Ports at a glance

| Port | Protocol | Used for |
| --- | --- | --- |
| 8765 | HTTP | The web app, Home Assistant Ingress, the health check |
| 8766 | HTTPS | The web app and the API on your network |

## Next step

Open the web app and follow [Getting started](getting-started.md). If something does not work, see
[Troubleshooting](troubleshooting.md).
