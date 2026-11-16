# M2 — Persistence, configuration, migrations

## Goal
Give the engine durable state so the supervisor (M3), the API (M5) and licensing (M11) can build on it: paired TVs,
rule sets, daily usage, overrides, events and settings. ADR 0007 fixes the stack: one SQLite file in the data
directory, SQLAlchemy 2 async, Alembic migrations at startup, pairing keys encrypted at rest.

## Product decisions
- A `Policy` is stored as a **versioned JSON document**, one row per rule set. The domain reads and writes it as a
  whole; schema evolution goes through a codec with round-trip tests.
- Authentication tables (admin account, sessions, API tokens) arrive with M5 in their own migration.
- No pruning of historical data for now: an expired license falls back to Free without data loss.

## Configuration (`tvbalance/config.py`)
`EngineConfig` (frozen dataclass: `host`, `port`, `web_dir`, `data_dir`) built by `EngineConfig.from_env`, with clear
errors for invalid values. `data_dir` defaults to `./data` (`TVBALANCE_DATA_DIR`, `/data` in the Add-on).

## Ports (`ports/storage.py`)
`TvStore`, `PolicyStore`, `UsageStore` (atomic upserts, safe under concurrent calls), `OverrideStore`, `EventLog`,
`SettingsStore`, grouped by `Storage`. `EventLog.append` has the same shape as `EventPublisher.publish`.

## Infrastructure (`infra/`)
- `db/engine.py`: async engine with `journal_mode=WAL`, `foreign_keys=ON` and a busy timeout on every connection.
- `db/types.py`: `UtcDateTime` rejects naive datetimes and returns aware UTC values (SQLite drops time zones).
- `db/tables.py`: SQLAlchemy Core tables (the domain uses frozen dataclasses): `policies`, `tvs`, `usage`,
  `overrides`, `events`, `settings`. Removing a TV cascades to its usage and overrides.
- `db/policy_codec.py`: `encode_policy` / `decode_policy` with a `version` field; unknown versions are rejected.
- `db/migrations/` inside the package (it ships in the wheel and the image), `0001_initial`, and
  `db/migrate.py` running Alembic programmatically, without an `alembic.ini`.
- `db/repositories.py`: SQLite implementations and `open_storage(config)`.
- `secrets.py`: `SecretBox` (AES-GCM) with a locally generated key in `data_dir/secret.key`; adapter credentials
  are stored encrypted and never appear in `repr` or logs.

## Out of scope
Authentication (M5), enforcement-state persistence (M3 decides), data pruning, migration from the prototype.

## Tests
Unit and property tests in `engine/tests/infra/`: config, pragmas, UTC type, `SecretBox`, codec round-trip with
`hypothesis`, migrations (upgrade, no drift between tables and revisions, downgrade and upgrade again) and
repositories (cascade, active overrides, concurrent upserts, credentials unreadable in the file).
CI measures branch coverage of `tvbalance.domain` and `tvbalance.infra` at 95 %.

## Commit sequence
Plan; configuration; engine and UTC type; secret box; policy codec; tables and migration; repositories and
`open_storage`; startup wiring, coverage gate and docs.
