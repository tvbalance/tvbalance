# M7: Discovery and guided pairing

## Goal
Let a parent add a TV from the Web UI (spec F1) and pair it again when its key is lost (F4): find TVs on the LAN or
type an address, follow the brand's instructions, store the key encrypted, name the TV and pick a rule set.

## Product decisions
- Discovery and pairing need a full admin; a PIN session never adds TVs.
- Discovery asks every installed adapter at once (testing-only adapters only when enabled). Each adapter is bounded by
  a timeout and isolated: one failing adapter is logged, never fatal. Results flag TVs that are already added.
- Entering the address by hand is always offered: multicast may be blocked (containers, VLANs).
- The TV is stored when pairing completes, with the discovered or typed name and no rule set. The last wizard step
  renames it and assigns a rule set through `PATCH tvs/{id}`.
- Pairing an existing TV again uses the same flow with `tv_id`: the credentials are replaced and its worker restarted.
- One pending pairing per host. A pairing expires after three minutes. Leaving the wizard cancels it.
- Events `tv_added` and `tv_paired` go through the event bus (stored, shown in activity, sent on the WebSocket).
- Per-brand instructions live in the web locales, keyed by adapter id with a generic fallback.

## Engine
- `app/pairing.py`: `PairingService` (discovery, sessions, background polling, persistence, events), started in the
  lifespan as `app.state.pairing` and stopped with it.
- `GET /api/v1/discovery`, `POST /api/v1/pairings`, `GET` and `DELETE /api/v1/pairings/{id}`.
- Host validation: a host name or IP address, no scheme, port or path.

## Web
Add-TV wizard (find or enter address, pair, finish), "Add a TV" from the empty dashboard and the header, "Pair again"
on TVs that need it, five locales.

## Out of scope
mDNS and DIAL discovery, Supervisor discovery (M9), QR or PIN-code pairing for brands other than LG, licensing and the
one-TV limit (M11).

## Tests
Engine: scripted pairing flows (complete, fail, expire, cancel), failing and slow discoverers, duplicates, unknown
adapter or TV, PIN session refused, re-pairing restarts the worker, events, shutdown. Web: discovery list, manual
form, polling, retry, cancel on leaving, finish step, re-pairing, locale parity.

## Commit sequence
1. Plan (this document).
2. Discover TVs from every installed adapter.
3. Pair a new TV in the background and store it.
4. Cancel and expire pairings; pair an existing TV again.
5. API documentation and regenerated web schema.
6. Web add-TV wizard.
7. Web entry points and re-pairing.
8. User guides and plan status.

## Hardware check
Local engine with the built UI (never the production PoC): search (the LG may not answer SSDP here), enter its
address, accept the prompt on the TV, name it, assign a rule set and see it live; then invalidate the key and use
"Pair again".
