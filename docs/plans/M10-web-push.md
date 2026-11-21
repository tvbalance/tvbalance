# M10: Web Push notifications

Status: in progress.

## Goal
Spec F11 and F4: a parent who installed the web app gets a notification when something needs attention, with a link
to the right page, even when the app is closed.

## Product decisions
- Events: `pairing_lost`, `tv_unreachable`, `blocked`, `time_warning`. All on by default, each switchable per device.
- Only full administrators (password login or Home Assistant Ingress) can subscribe a device; notifications carry
  management links.
- Web Push needs a secure context. Over plain `http://ip:8765` the settings card explains why it is unavailable;
  it works through Ingress served over HTTPS and on localhost. HTTPS on the LAN is M18.

## Engine
- `infra/webpush.py`: VAPID keys (P-256, ES256 JWT), RFC 8291 `aes128gcm` payload encryption, a sender that tells
  delivered, gone (404/410) and failed apart. Only `cryptography` and `httpx`; no push library.
- VAPID keys are created on first use and kept in the sealed secret settings.
- Table `push_subscriptions` (migration `0004`); the subscription `auth` secret is sealed at rest.
- `app/notifications.py`: a lifespan task reads the event bus, builds localized texts and a link, sends to every
  subscription that enabled the event. Same TV and event are not repeated within 10 minutes. Gone subscriptions are
  removed; five failures in a row remove one too.
- API under `/api/v1/push`, full admin only: key, list, create (upsert by endpoint), update events, delete, test.

## Web
Service worker through `injectManifest` (precache plus `push` and `notificationclick`), a Notifications card in
Settings with support detection, permission handling, per-event switches, test and removal; five languages.

## Tests
RFC 8291 test vector, sender outcomes with a mock transport, storage round trip and sealing, notifier filtering,
language, link, dedup and cleanup, API validation and permissions, web card states.

## Commit sequence
1. Plan (this document).
2. Web Push protocol: VAPID, encryption, sender.
3. Subscription storage and migration.
4. Notifier and localized texts.
5. API and OpenAPI.
6. Service worker.
7. Settings card and translations.
8. Docs and plan status.
