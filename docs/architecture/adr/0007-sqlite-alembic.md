# ADR 0007: SQLite with Alembic migrations

- Status: accepted
- Date: 2026-11-16

## Context

The Engine must run on small devices with zero administration and survive Add-on updates, where only the data directory persists.

## Decision

Persist configuration, usage, events and sessions in a single SQLite file under the data directory, accessed through SQLAlchemy 2 async. Schema changes are managed by Alembic migrations that run at startup. Pairing keys are encrypted at rest with a locally generated key.

## Consequences

Simple backup and restore, no external service. Writes are serialized; acceptable at this scale. Migrations must be tested from every released schema.
