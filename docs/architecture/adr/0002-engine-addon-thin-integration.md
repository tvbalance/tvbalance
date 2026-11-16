# ADR 0002: Standalone Engine, Add-on and thin integration

- Status: accepted
- Date: 2026-11-16

## Context

Home Assistant Add-ons exist only on HA OS and Supervised, while vendoring a full engine inside a custom integration causes dependency conflicts and couples our release cadence to Home Assistant. A prototype that vendored its core inside the Home Assistant process confirmed both problems.

## Decision

Build a standalone Engine (Docker image, versioned HTTP and WebSocket API). Package it as a Home Assistant Add-on with Ingress. Ship a thin custom integration that only talks to the Engine API through the published tvbalance-client library, with no domain logic and no protocol code.

## Consequences

Works for HA OS, Supervised, Container and Core users, and for non-HA users. The API becomes a product surface that needs versioning discipline. Entities are created by a real integration, never by state injection.
