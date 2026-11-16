"""Alembic environment.

At runtime the caller hands in a live connection (``config.attributes["connection"]``). For
development (``alembic -c engine/alembic.ini revision --autogenerate``) it opens its own from
``sqlalchemy.url``.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, engine_from_config, pool

from tvbalance.infra.db.tables import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


connection = config.attributes.get("connection")
if connection is not None:
    _run(connection)
else:
    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        _run(connection)
        connection.commit()
