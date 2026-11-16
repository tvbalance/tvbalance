# ADR 0001: Monorepo with uv and npm

- Status: accepted
- Date: 2026-11-16

## Context

The engine, adapters, client, Home Assistant integration, Add-on and web UI evolve together and share contracts (the OpenAPI schema, the capability model). Splitting them early multiplies release overhead for a small team.

## Decision

Use one repository. Python code is a uv workspace (engine, adapters, client) with a single lockfile; the web UI is an npm project under web/. The closed-source Pro module lives in a separate private repository.

## Consequences

One CI pipeline and atomic cross-component changes. The repository grows large; path-filtered CI jobs keep builds fast. The Home Assistant integration still ships through its own public repository mirror at release time, because HACS requires a single-integration layout.
