# Changelog

## Unreleased

- HTTPS on port 8766 with a certificate from a local authority that TVBalance creates and renews. Use your own certificate from `/ssl`, or turn it off, in the Add-on options. HTTP and Ingress keep working on port 8765.
- The Add-on announces itself to Home Assistant, so the integration is set up without a URL or token.
- Web Push notifications for pairing lost, TV unreachable, blocked content and time warnings (Settings > Notifications).
- Image labels and build arguments for the Supervisor and for ghcr.
