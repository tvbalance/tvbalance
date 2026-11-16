# TVBalance — Product Specification (MVP v1.0)

> Scope: what we build and why. Technical design lives in `docs/architecture/`.

## 1. Context and positioning

TVBalance helps parents set healthy, enforceable viewing rules on shared family TVs, locally, with first-class
Home Assistant support.

**Market (checked November 2026).** Competitors exist but are single-brand and isolated: a Homey app for LG
(daily quota), a Windows app for Roku, an Android TV app on subscription, and a YouTube filter for Home Assistant.
**Differentiation:** multi-brand, Home Assistant native, channel/EPG-aware, local-first with no subscription.

**Target users:** parents running Home Assistant (US/EU) who want a five-minute setup; secondarily Docker/NAS
users without Home Assistant.

## 2. Product decisions

| Topic | Decision |
|---|---|
| Name | TVBalance, always paired with the tagline (trademark and domain checks pending) |
| Distribution | Home Assistant first: Engine (multi-arch Docker) + Add-on + thin HACS integration |
| MVP brands | LG webOS (stable), Roku TV, Google/Android TV, Samsung Tizen (beta until verified on hardware) |
| UI | Web UI and PWA, React + TypeScript + Vite, Ingress compatible |
| License | Core, adapters, HA integration: Apache-2.0. Pro module is closed source |
| Pro pricing | One-time per household, offline Ed25519 license, sold through a merchant of record |
| Profiles | Rule sets (School, Weekend, Holidays, Sick day), not per child (v2) |
| Auth outside HA | Admin account created at first start; quick unlock with PIN or passkey; under Ingress the HA user applies |
| Notifications | HA events/entities and blueprints for the Companion app; Web Push from the PWA |
| Languages | EN (default), IT, DE, FR, ES; automatic detection (HA, then browser) with manual override |

## 3. Functional requirements

### F1. Zero-friction onboarding (Free)
- One-click Add-on install; prebuilt images for amd64 and aarch64; start in under 30 s.
- Automatic LAN discovery (SSDP/mDNS/DIAL), brand identification, guided pairing with per-brand instructions.
- Country, language and time zone detected from Home Assistant or the browser.
- Built-in diagnostics: connection test, detected capabilities, anonymized support bundle.
- Capability matrix shown to the user (for example, "on-screen messages: not available on Roku").

### F2. Rules (Free)
- Weekly time windows (allowed/blocked) and special days.
- App blocking (from the installed-app list, with icons), input blocking (HDMI/console), channel blocking by
  number or name where the brand exposes it, and an allow-list mode.
- Semantics proven in the proof of concept: a day without windows is fully blocked; windows crossing midnight
  belong to their starting day; debounce; no ping-pong between fallback targets.

### F3. Time (Free basic / Pro advanced)
- Free: one daily budget per TV, pre-expiry warnings (for example 10 and 5 minutes), manual bonuses.
- Pro: per-app or per-category budgets, per-weekday budgets, rollover of unused minutes, per-profile budgets.

### F4. Enforcement (Free)
- Configurable escalation: on-screen warning, redirect (home, allowed app or channel), power off.
- Protections: cooldowns, cap on repeated power-offs, no loops.
- Circumvention coverage in v1:
  - input/app switching with the remote and powering on outside the window are detected and corrected;
  - casting from a phone is treated as a foreground app and blocked like any app;
  - a TV removed from the network raises a "TV unreachable during policy" event; optional Home Assistant smart-plug automation;
  - factory reset or lost pairing raises an event and a parent notification with a re-pairing link.

### F5. Parent controls (Free)
- Temporary override (allow/block for N minutes or until midnight), bonus, instant pause.
- From the Web UI/PWA, from Home Assistant entities and services, and from automations.

### F6. Profiles and calendar (Pro)
- A profile is a rule set, activated manually for a duration, from a calendar, or from an automation.

### F7. Content and EPG (Pro)
- Zero-config: guides load automatically per country from a curated, signed, versioned catalog that updates
  without an Engine release. Automatic channel-to-guide matching; manual fix only as a fallback.
- The TV's native guide is the primary "what is on now" source where available.
- Blocking by title, series or keyword; browsable guide with per-program block/unblock.
- Constraint: source licenses and terms must be verified per country before inclusion.

### F8. Multi-TV (Free: 1 TV / Pro: unlimited)
- Rules per TV or shared; budgets per TV or per household (Pro).

### F9. Reports (Free basic / Pro)
- Free: today's usage, last 7 days, event log.
- Pro: unlimited history, weekly report, usage by app and channel.

### F10. Home Assistant (Free, growth lever)
- Native integration with discovery of the Engine/Add-on: per TV, entities for state, current app/channel/program,
  minutes used/left, block active, active profile, enforcement switch, bonus; services; events
  (`time_warning`, `blocked`, `tv_unreachable`, `pairing_lost`).
- Sensitive actions are protected by Home Assistant user permissions (admin). No PIN in service data.
- Ready-made blueprints: light warning at 5 minutes, Companion notification, physical button to bonus, calendar to profile.
- The Ingress panel is the same Web UI as the Engine.

### F11. Web UI and PWA (Free)
- Mobile-first, light/dark themes, accessible (WCAG AA), installable, Web Push.
- Works through Ingress and directly on the LAN (HTTPS with a locally managed certificate).

### F12. Pro licensing
- Purchase through a merchant of record, paste the key in the UI, verified offline with Ed25519.
- Configuration is always savable; the gate applies only at runtime; an expired license falls back to Free without data loss.

## 4. Non-functional requirements

- **Local-first:** no mandatory cloud; the only optional outbound traffic is the EPG catalog (Pro) and update checks. No telemetry by default.
- **Reliability:** hard timeouts on every TV call, supervised reconnection, a loop that can never block; enforcement within about 5 s.
- **Footprint:** runs on a Raspberry Pi 4 / Home Assistant Green (target under 150 MB RAM).
- **Security:** secrets never in clear on disk or in logs, revocable sessions, rate limiting, HTTPS on the LAN, documented threat model.
- **Quality:** TDD, contract tests for every adapter, CI on every pull request, automated releases, semantic versioning.
- **Home Assistant compatibility:** the last six monthly releases, CI against the minimum and the latest.
- **Documentation:** multilingual user guide, per-brand guides, troubleshooting, FAQ, adapter contributor guide.

## 5. Out of scope for v1

Per-child profiles, native store apps (PWA only), hardware box, DNS/router filtering, cloud relay for remote
access, Fire TV, Apple TV, cast-only Chromecast, Vizio and Hisense (candidates for v1.x through the adapter SDK).

## 6. Release criteria for v1.0

- LG webOS verified on real hardware; Roku, Google TV and Samsung labeled beta with a tester program.
- Add-on installable from a custom repository; integration available in HACS; Web UI in five languages; user guide published.
- Pro purchase and activation working end to end; CI green; no known blocking bug.

## 7. Main risks

1. Per-brand feasibility (Samsung foreground-app query on recent models, Roku network-control mode, Google TV app detection without ADB). Spikes are mandatory before detailed design.
2. No non-LG hardware in-house: dependence on beta testers.
3. EPG source licensing per country.
4. Trademark and SEO ("TV balance" also means audio balance).
