# ADR 0004: Pure domain and engine-enforced timeouts

- Status: accepted
- Date: 2026-11-16

## Context

Rule evaluation must be exhaustively testable, and a single hung TV call must never freeze supervision. The prototype wedged in a ghost online state because a websocket send to a dead peer never returned.

## Decision

The domain package performs no I/O: evaluate() and plan_actions() are pure functions over explicit inputs, with an injectable clock. Every adapter call goes through the engine's TVSession wrapper that applies hard timeouts and maps failures to typed errors. Adapters are not trusted to bound their own calls.

## Consequences

Property-based tests (hypothesis) cover the rules. Timeouts are uniform and centrally tuned. The wrapper adds a small abstraction layer between supervisor and adapters.
