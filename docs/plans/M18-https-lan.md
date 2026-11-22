# M18: HTTPS on the LAN

Status: done. Real devices (phone, Home Assistant over HTTPS) still need a manual check.

## Goal
Serve the web app and the API over HTTPS on the local network with a locally managed certificate, so the web app
gets a secure context (service worker, Web Push), cookies are `Secure` and credentials are not sent in clear.

## Product decisions
- Default `auto`: the Engine creates a local CA constrained to private names and addresses (X.509 Name Constraints)
  and issues a server certificate that renews itself. Users install the CA on their devices.
- Bring your own certificate: `TVBALANCE_TLS_CERTFILE` / `TVBALANCE_TLS_KEYFILE` (for example `/ssl` in Home Assistant).
- `off` disables HTTPS.
- HTTP on 8765 stays open (Ingress, health check, Add-on discovery). The web app shows a banner that points to HTTPS.
- The Home Assistant integration can use HTTPS and pins the CA after the user confirms its fingerprint.

## Parts
- Engine: `infra/tls.py` (CA, server certificate, renewal, fingerprint, iOS profile), TLS configuration,
  `app/tls.py` (`TlsManager`), a second uvicorn server with hot certificate reload.
- API: `https_port` in `/info`, `/tls` status, public CA download, CA rotation.
- Web: banner, Secure connection card in Settings, hint in Notifications.
- Client 0.2.0: `ssl_context`, CA download and fingerprint helpers.
- Integration: HTTPS with a pinned CA and reauth when the CA changes.
- Add-on: port 8766, options, `ssl` mapping.

## Commit sequence
1. Plan (this document).
2. Local certificates.
3. TLS configuration.
4. `TlsManager` and lifespan.
5. HTTP and HTTPS servers with hot reload.
6. API and OpenAPI.
7. Web.
8. Client.
9. Home Assistant integration.
10. Add-on.
11. Documentation and threat model.
