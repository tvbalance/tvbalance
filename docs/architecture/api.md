# Engine API v1

The Engine serves a JSON API under `/api/v1`. The authoritative schema is
`engine/openapi.json` (regenerated with `uv run python engine/scripts/export_openapi.py`; a test
fails when it drifts). This page explains what the schema cannot: how callers authenticate, the
error envelope and the WebSocket protocol. The design rationale is in
[ADR 0005](adr/0005-authentication.md).

## Authentication

Every endpoint except the ones below needs a credential.

| Public endpoint                         | Purpose                                         |
| --------------------------------------- | ----------------------------------------------- |
| `GET /health`                           | Add-on watchdog                                 |
| `GET /info`                             | `{version, api_version}`                        |
| `GET /auth/state`, `POST /auth/setup`   | First-run setup (only until an admin exists)    |
| `POST /auth/login`, `POST /auth/pin-login` | Sign in                                      |

A request is authenticated by the first mechanism that applies:

1. **Ingress headers** `X-Remote-User-Id` / `X-Remote-User-Name`, trusted only when the peer is
   listed in `TVBALANCE_INGRESS_TRUSTED` (the add-on sets `172.30.32.2`). The caller is a full
   admin. From any other peer the headers are ignored.
2. **Bearer token** `Authorization: Bearer tvb_…`. Created by an admin session with
   `POST /auth/tokens`, shown once, stored hashed. Scopes: `read`, `control` (override, bonus,
   pause) and `admin` (TV, policy and settings writes). A wrong token is a 401; it does not fall
   back to the cookie.
3. **Session cookie** `tvb_session`. `POST /auth/login` (password) gives a full admin session;
   `POST /auth/pin-login` gives a PIN session with the `read` and `control` scopes only and no
   access to passwords, PINs, tokens or sessions. The PIN is locked after 5 failures until a
   password login. Unsafe methods (`POST`, `PUT`, `PATCH`, `DELETE`) on a cookie session must send
   the `tvb_csrf` cookie's value in the `X-TVBalance-CSRF` header; Bearer and Ingress are exempt.

Password and PIN logins are rate limited (`429` with `Retry-After`).

## Errors

Failures use one envelope with a stable `code`:

```json
{"error": {"code": "not_authenticated", "message": "…", "details": null}}
```

Codes: `not_authenticated` (401), `forbidden` (403), `setup_required`, `rate_limited` (429),
`validation_failed` (422), `not_found` (404), `conflict` (409).

## Endpoints

- **TVs:** `GET /tvs`, `GET /tvs/{id}` (record plus live status); `PATCH` and `DELETE /tvs/{id}`
  need `admin`. A TV is added by pairing it (below).
- **Discovery and pairing** (`admin`; a PIN session is refused):
  - `GET /discovery` searches the network with every installed adapter (a few seconds) and returns
    `{adapter_id, adapter_name, host, name, model, already_added}`. Overlapping searches share one scan.
  - `POST /pairings` starts a pairing and answers 201 `{id, state, adapter_id, host, tv_id,
    expires_at}`. Send `adapter_id`, `host` (a host name or IP address, nothing else) and an optional
    `name` to add a TV, or `tv_id` to pair a stored TV again. Errors: 404 (unknown adapter or TV), 409
    `tv_exists` or `adapter_mismatch`, 422. A pairing already waiting on the same address is returned
    as is.
  - `GET /pairings/{id}`: `state` is `waiting_for_user`, `completed`, `failed` or `expired`; `tv_id`
    is set once the TV is stored. The person has three minutes to accept on the TV; finished pairings
    can be read for ten minutes.
  - `DELETE /pairings/{id}` abandons it (204); a TV already stored stays.
  - The TV and its key are stored when pairing completes. Events `tv_added` and `tv_paired` (a
    stored TV paired again) go through the log and the WebSocket.
- **Policies:** `GET /policies`, `GET /policies/{id}`; `POST /policies` and `PUT /policies/{id}`
  need `admin` and answer 422 with the domain's issue codes when the policy is invalid.
- **Control** (`control` scope): `POST /tvs/{id}/override` (`allow`, then `minutes` or
  `until_midnight`), `DELETE /tvs/{id}/override`, `POST /tvs/{id}/bonus` (`minutes`),
  `POST /tvs/{id}/pause` (`minutes`, default 30). Times are returned in UTC.
- **Activity** (`read`): `GET /tvs/{id}/usage?days=` and `GET /events?tv_id&since&limit`.
- **Settings:** `GET /settings` (`read`), `PUT /settings` (`admin`): `language`, `timezone`.
- **Auth management:** `GET /auth/me`, `POST /auth/logout`, `PUT /auth/password`,
  `PUT`/`DELETE /auth/pin`, `GET`/`DELETE /auth/sessions[/{id}]`,
  `GET`/`POST`/`DELETE /auth/tokens[/{id}]`.

## Live events: `GET /api/v1/events/ws`

A WebSocket authenticated at the handshake with the same credentials (a browser sends its cookie;
it must come from the Engine's own origin). Every message is a JSON object
`{"type", "tv_id", "at", "payload"}`:

- `status`: sent once per TV on connect; `payload` is the TV's status as in `GET /tvs/{id}`.
- `ping`: every 30 seconds while idle.
- anything else is an event as stored in the log (`blocked`, `time_warning`, …).

The Engine closes the socket with code **4401** when the credential is missing, signed out,
revoked or expired, and **4403** when it lacks the `read` scope or a cookie arrives from a foreign
Origin.

The `tvbalance-client` package wraps all of this (`TVBalanceClient(url, token)`).
