# ADR 0008: Internationalization

- Status: accepted
- Date: 2026-11-16

## Context

The product targets the US and the EU from day one, and Home Assistant users expect their own language without configuration.

## Decision

Ship English (default), Italian, German, French and Spanish. The language is detected from Home Assistant, then the browser, with a manual override. The web UI uses i18next with ICU message format; the Engine localizes only user-facing strings it generates (for example on-screen messages); Home Assistant strings use the standard translations folder. Translations are plain JSON files so that community tools can be used later.

## Consequences

Every user-facing string must be a key. CI checks that all locales have the same keys. Quality of non-English text depends on review.
