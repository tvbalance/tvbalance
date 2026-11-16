# ADR 0005: Authentication model

- Status: accepted
- Date: 2026-11-16

## Context

The UI is reachable directly on the LAN and through Home Assistant Ingress, and the Home Assistant integration needs machine access. A shared PIN passed as service data leaks into the event bus and traces.

## Decision

Direct access uses an admin account (argon2 hashed) with revocable cookie sessions; a quick-unlock PIN or passkey is a convenience layer on top, never the root of trust. The Home Assistant integration uses a scoped API token obtained during config flow, ideally through Supervisor discovery. Under Ingress, requests carrying the Supervisor-injected user headers are authenticated as that Home Assistant user. Sensitive Home Assistant services rely on Home Assistant admin permissions, not on secrets in service data.

## Consequences

No duplicated user system under Ingress, and no secret travels in service calls. The Ingress trust boundary must be enforced by accepting those headers only from the Supervisor network.
