# ADR 0006: Open core with Apache-2.0

- Status: accepted
- Date: 2026-11-16

## Context

The business model is a one-time Pro license. The Home Assistant community expects local features to stay free and distrusts artificial paywalls. Hiding code is not a real protection for interpreted Python.

## Decision

The core, the adapters, the client and the Home Assistant integration are Apache-2.0. License verification (Ed25519, offline) is open. Pro features live in a separate closed-source package installed into the official image through an entitlements extension point. The value sold is convenience, curated data (EPG catalog) and maintenance.

## Consequences

Community contributions and trust are maximized. Anyone can fork and enable Pro features by rebuilding; this is accepted. Free tier must stay genuinely useful (single TV, schedules, base time budget).
