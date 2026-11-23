# Changelog

## 0.1.0

First release.

- Supervision of LG webOS TVs: time windows, daily budgets, and blocking of apps, inputs and channels, with on-screen warnings and a redirect or power-off when something is blocked.
- Web app in English, Italian, German, French and Spanish: dashboard with parent controls, rule editor, activity log and settings.
- Home Assistant integration with a device per TV, sensors, a pause button, admin-only services, events and blueprints.
- TVBalance Pro (one license for the household): more than one TV, profiles and a calendar, advanced budgets, long history and a weekly report. Free supervises one TV.
- Documentation site and user guide in five languages, with an adapter guide and API reference for developers.
- HTTPS on port 8766 with a certificate from a local authority that TVBalance creates and renews. Use your own certificate from `/ssl`, or turn it off, in the Add-on options. HTTP and Ingress keep working on port 8765.
- The Add-on announces itself to Home Assistant, so the integration is set up without a URL or token.
- Web Push notifications for pairing lost, TV unreachable, blocked content and time warnings (Settings > Notifications).
- Image labels and build arguments for the Supervisor and for ghcr.
