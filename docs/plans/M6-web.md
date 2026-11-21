# M6: Web UI

## Goal
Turn the `web/` skeleton into the parent-facing product (spec F5, F9 free, F11, and F1 minus pairing): first-run
setup, sign-in, a live dashboard with parent controls, shared rule sets with an editor, activity, and settings.
It works behind Home Assistant Ingress and directly on the LAN, on phones first, in five languages.

## Product decisions
- Onboarding creates the admin, picks language and time zone and offers a first rule set from a preset. Adding a TV
  and pairing are M7: with no TV the dashboard shows an empty state.
- Rules are named sets shared between TVs (the `policies` API); each TV picks one.
- App, input and channel pickers read the TV's own inventory and fall back to free text when the TV is offline.
- Sensitive settings (password, PIN, sessions, API tokens) need a full admin; a PIN session sees the controls
  (read and control scopes) but not them.
- No charting library: usage bars are plain CSS.

## Engine additions
- `GET /api/v1/tvs/{id}/inventory` (read): apps, inputs and channels from the live session, cached five minutes in the
  worker; `409 tv_offline` when the TV is not connected.
- `GET /api/v1/tvs/{id}/apps/{app_id}/icon`: proxies the app icon from the TV's own host only, so icons load under
  Ingress and HTTPS.

## Web foundations
- `src/api/`: a fetch wrapper with relative URLs only, the CSRF header taken from `auth/me`, the error envelope as
  `ApiError`, and a global 401 handler; React Query hooks; a reconnecting WebSocket client that patches the TV cache.
- shadcn/ui components added as needed, light and dark themes, mobile-first, WCAG AA.
- `HashRouter` (Ingress safe) behind an auth gate: setup, sign-in or straight in under Ingress.
- Every string in the five locales; initial language from the saved setting, then the browser.

## Pages
Welcome (3 steps), sign-in (password and PIN), dashboard (live status, pause, bonus, allow or block, clear),
TV details (policy, enabled, seven-day usage, events, remove), rules (list and tabbed editor: schedule, time,
content, advanced), activity, settings (language, time zone, password, PIN, sessions, API tokens, theme, sign out),
system (version and adapters).

## Out of scope
TV pairing and discovery (M7), Web Push (M10), LAN HTTPS (M9), passkeys, licensing and the one-TV limit (M11),
profiles and calendar (M16), advanced reports.

## Tests
Engine: inventory and icon proxy tests keep `tvbalance.api` above 95%. Web: Vitest with a stubbed `fetch` and a fake
`WebSocket` covering the auth gate, onboarding, dashboard actions with the CSRF header, the rule editor including
422 field errors, token creation, and locale key parity.

## Commit sequence
1. Plan (this document).
2. List a TV's apps, inputs and channels.
3. Proxy TV app icons.
4. API layer, auth gate and live events.
5. UI components, theme and navigation.
6. First-run setup and sign-in.
7. Dashboard and parent controls.
8. Rule sets and the rule editor.
9. TV details and activity.
10. Settings, sessions and API tokens.
11. User guide and plan status.

## Hardware check
Local engine with the built UI (never the production PoC): onboard in the browser, add the LG as in M5, pause it for
five minutes from the dashboard, edit a rule with the real app list and icons, sign in with the PIN on a narrow
viewport, and check the dark theme.
