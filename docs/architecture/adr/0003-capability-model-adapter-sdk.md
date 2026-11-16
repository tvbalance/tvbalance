# ADR 0003: Capability model and adapter SDK

- Status: accepted
- Date: 2026-11-16

## Context

TV brands differ widely: some cannot show messages, change channels or report the foreground app. A fat TV interface that assumes everything works hides these differences and breaks in production.

## Decision

Each adapter declares an AdapterInfo (id, brand, maturity stable/beta/experimental, a set of Capability values). Adapters are separate packages discovered through the tvbalance.adapters entry point group and must pass a shared contract test suite. The domain plans actions from the capabilities available and the UI shows a capability matrix.

## Consequences

Honest per-brand behavior and a clear contributor path. Contract tests need recorded fixtures per brand. Capability sets must be confirmed by feasibility spikes before they are promised.
