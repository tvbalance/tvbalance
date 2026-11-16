# M5: API v1, authentication, WebSocket events

## Goal
Expose the engine through a versioned, authenticated HTTP API and a WebSocket event stream, following ADR 0005.
The Web UI (M6), the pairing wizard (M7), the Home Assistant integration (M8), the Add-on (M9) and Web Push (M10)
all build on it. The API sits on top of `Supervisor.refresh/status`, `EventBus.subscribe` and the storage ports.

## Product decisions
- Direct access uses an admin account (argon2) with revocable cookie sessions. A quick-unlock PIN is a convenience
  layer, never the root of trust. The Home Assistant integration uses a scoped API token. Under Ingress the
  Supervisor-injected user headers authenticate the request, only from the Supervisor network.
- One milestone, small commits. LAN HTTPS is deferred to M9; `Secure` cookies apply only when the request is HTTPS.
- Adding a TV and pairing through the API belong to M7. M5 lists, edits and removes existing TVs.

## Authentication model
- **Bootstrap:** while no admin exists only `GET auth/state` (`{setup_required}`) and `POST auth/setup` answer.
  Setup works once (409 afterwards). Passwords have at least 10 characters.
- **Sessions:** 32 random bytes in the `tvb_session` cookie (HttpOnly, SameSite=Strict); the database keeps only the
  SHA-256 of the token. Sliding expiry of 30 days, single revocation and "log out everywhere". Cookie-authenticated
  mutations need the `X-TVBalance-CSRF` header (double submit); Bearer and Ingress are exempt.
- **PIN:** 4 to 8 digits (argon2), set only from a full admin session. A PIN login creates a `pin` session of 12 h
  without the heavy admin rights (password, PIN, tokens, sessions). Stricter rate limit; after 5 failures the PIN is
  locked until the next password login.
- **API tokens:** `tvb_` plus 32 random bytes (base64url), shown once, stored as SHA-256. Scopes `read`, `control`
  (overrides, bonus, pause) and `admin`. Home Assistant uses `control`. Managed only from a full admin session.
- **Ingress:** `X-Remote-User-Id`, `X-Remote-User-Name` and `X-Ingress-Path` are honored only when the peer is in
  `TVBALANCE_INGRESS_TRUSTED` (default empty; the Add-on sets `172.30.32.2`). The Home Assistant user counts as a
  full admin. The same headers from an untrusted peer are ignored and logged.
- **Rate limiting:** in memory per IP and account, exponential backoff on password and PIN login, `429` with
  `Retry-After`.
- `Principal(kind: admin | pin | token | ingress, scopes)`; the FastAPI dependency `require(scope)` guards routes.
  Resolution order: trusted Ingress, Bearer, cookie.
- `/api/v1/health` stays public (Add-on watchdog). `/api/v1/info` keeps only version data; the adapter list moves
  to an authenticated system route.

## Storage (migration `0003_auth`)
- Tables `admin` (single row: password hash, PIN hash, PIN failures, updated at), `sessions` (id, token hash, kind,
  created, last seen, expires, user agent) and `api_tokens` (id, name, token hash, scopes, created, last used,
  revoked).
- Port `AuthStore`, exposed as `Storage.auth`; SQLite implementation next to `infra/db/repositories.py`.
- Hashing with `argon2-cffi` in `infra/passwords.py`.

## Services (`app/auth.py`, `app/ratelimit.py`)
Framework-free logic: setup, password and PIN verification, issue, rotate and revoke of sessions and tokens, and the
rate limiter, all with the injected `Clock`.

## API layer (`api/`)
- `api/deps.py`: storage and supervisor accessors, `current_principal`, `require(scope)`, CSRF check.
- Routers in `api/routes/`: `auth`, `system`, `tvs`, `policies`, `control`, `activity`, `events_ws`. Pydantic schemas
  move to `api/schemas/`.
- Uniform errors `{error: {code, message}}` with stable codes: `not_authenticated`, `forbidden`, `setup_required`,
  `rate_limited`, `validation_failed`, `not_found`, `conflict`.

## REST endpoints (`/api/v1`)
- **auth:** `GET auth/state`, `POST auth/setup`, `POST auth/login`, `POST auth/pin-login`, `POST auth/logout`,
  `GET auth/me`, `PUT auth/password`, `PUT auth/pin`, `DELETE auth/pin`, `GET|DELETE auth/sessions[/{id}]`,
  `GET|POST|DELETE auth/tokens[/{id}]`.
- **tvs** (read, admin to write): `GET tvs`, `GET tvs/{id}` (record plus `TvStatus`), `PATCH tvs/{id}` (name,
  enabled, policy; triggers `refresh`), `DELETE tvs/{id}`.
- **policies** (read, admin to write): `GET policies`, `POST policies`, `GET|PUT policies/{id}`. The schema mirrors
  `infra/db/policy_codec.py`; `validate_policy` failures return `422` with the `IssueCode` values. Saving refreshes
  the TVs that use the policy.
- **control** (control): `POST tvs/{id}/override` (allow or block, minutes or until midnight),
  `DELETE tvs/{id}/override`, `POST tvs/{id}/bonus`, `POST tvs/{id}/pause`. The worker reads overrides and usage on
  every tick, so `refresh(id)` makes the effect immediate.
- **activity** (read): `GET tvs/{id}/usage?days=7`, `GET events?tv_id&since&limit`.
- **settings** (admin): `GET|PUT settings` (`language` for now).

## WebSocket (`GET /api/v1/events/ws`)
Authenticated at the handshake with the same chain. Sends a `status` message per TV, then every `BusEvent` as
`{type, tv_id, at, payload}`; ping every 30 s; closes with `4401` when the session or token is revoked. Needs
`uvicorn[standard]` for a WebSocket backend.

## Client, web and Add-on
- `tvbalance_client`: `AuthenticationError` on 401/403, `tvs()`, `tv()`, `override()`, `bonus()`, `pause()`,
  `events()`. The Home Assistant config flow gains the `invalid_auth` error only; entities and services are M8.
- `engine/openapi.json` and the web API types regenerated; `web/src/api/client.ts` follows the new `info` shape.
- The Add-on start script sets `TVBALANCE_INGRESS_TRUSTED`.

## Out of scope
LAN HTTPS (M9), passkeys, login and settings UI (M6), adding and pairing TVs (M7), Home Assistant entities and
services (M8), Supervisor discovery (M8/M9), multiple users.

## Tests
- Shared engine fixtures in `engine/tests/conftest.py` (the supervision helpers, `app_client`, `admin_client`).
- Storage, migration `0003`, auth service and rate limiter with `FakeClock`.
- API: setup once, login, CSRF, revocation, PIN lockout, token scopes, trusted and untrusted Ingress, TVs, policies
  (`422` with issue codes), override then refresh then status, usage and events, WebSocket handshake, delivery and
  `4401` on revocation.
- `tvbalance.api` joins the 95% coverage gate in CI.

## Commit sequence
1. Plan (this document).
2. Share engine test fixtures.
3. Store admin, sessions and API tokens.
4. Authentication service and rate limiter.
5. Authenticate API requests.
6. Expose TVs and policies.
7. Overrides, bonus and pause.
8. Usage, events and settings.
9. Stream events over WebSocket.
10. Client authentication and control, `invalid_auth`.
11. Regenerate OpenAPI and web types, Add-on environment.
12. Document the API and gate `tvbalance.api` on coverage.

## Hardware check
On a local engine (never the production PoC): set up the admin, create a `control` token, block a paired LG for five
minutes through `POST tvs/{id}/override`, see the message and redirect, receive `blocked` on the WebSocket, then
revoke the token and confirm `401` and the `4401` close.
