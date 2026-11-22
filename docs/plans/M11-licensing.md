# M11: Licensing and entitlements

Status: done. The production public key is still to be generated and added to `TRUSTED_PUBLIC_KEYS`
(see operations/licensing.md).

## Goal
Spec F12 and ADR 0006: a one-time Pro license per household, verified offline with Ed25519. The gate applies only at
runtime: configuration is always savable, and an expired or removed license falls back to Free without data loss.
Today the only Free/Pro difference is multi-TV (F8); the real Pro features arrive with M15/M16 on top of the
`Entitlements` port.

## Product decisions
- Checkout: the UI shows a "Buy Pro" button that opens a configurable URL. Keys are signed by hand with a CLI
  script. No merchant integration yet.
- Free with several TVs: only the oldest enabled TV (`created_at`, then `id`) is supervised. The others stay
  configurable but inert and are marked "Requires Pro".
- Validity: perpetual, with an optional `expires_at` for trials and temporary licenses.

## Key format
`b64url(payload_json).b64url(signature)`, compact JSON with sorted keys. Payload v1:
`{"v":1,"product":"tvbalance","tier":"pro","license_id":"<uuid>","licensee":"<name>","issued_at":"<iso>","expires_at":null|"<iso>"}`.
Trusted public keys are embedded as a tuple so they can be rotated; verification tries each one. The private key
never enters the repository.

## Engine
- `infra/licensing.py`: `verify_license`, `sign_license`, `generate_keypair`, `LicenseError`, `LicensePayload`.
- `app/licensing.py`: `LicenseService` implements `Entitlements`. The key lives in the sealed secret settings, so
  no migration is needed. States: `none`, `active`, `expired`, `invalid`. An expiry task publishes
  `license_changed` and refreshes the supervisor.
- `Supervisor` admits only the first `max_tvs()` eligible TVs; `plan_limited(tv_id)` reports the rest.
- API under `/api/v1/license`: read (read scope), set and remove (full admin). `TvOut.plan_limited`.

## Web
A License card in Settings (plan, licensee, expiry, paste or remove a key, Buy Pro), a "Requires Pro" badge on
limited TVs, a notice in the add-TV wizard, five languages.

## Out of scope
Merchant webhooks and automatic key delivery, the closed Pro package loader (M15/M16), Home Assistant entities
for the plan.

## Tests
Round trip, tampered and unknown-key signatures, malformed keys, wrong product or tier, key rotation, expiry with a
fake clock, supervisor admission (Free, Pro, expiry, disabling the oldest TV), API permissions and errors, web card
and badges.

## Commit sequence
1. Plan (this document).
2. License cryptography.
3. CLI script.
4. License service.
5. Supervisor gate.
6. API and OpenAPI.
7. Web UI.
8. Documentation.

## Verification
Engine: `pytest`, `ruff`, `mypy` on `src`, coverage at or above 95%. Web: tests, lint, typecheck, regenerated
OpenAPI types with no leftover diff. Local run with the fake adapter: two TVs in Free supervise one; activating a
test key supervises both; an expired key goes back to Free.
