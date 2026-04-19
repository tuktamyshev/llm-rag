"""Alembic environment configuration.

Reads DATABASE_URL from the environment (same as the app) and registers
all SQLAlchemy models so that autogenerate can detect schema changes.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import Base  # noqa: E402

# Import all models so Base.metadata is complete
from modules.users import models as _users  # noqa: E402,F401
from modules.projects import models as _projects  # noqa: E402,F401
from modules.sources import models as _sources  # noqa: E402,F401
from modules.ingestion import models as _ingestion  # noqa: E402,F401
from modules.embeddings import models as _embeddings  # noqa: E402,F401
from modules.vectordb import models as _vectordb  # noqa: E402,F401
from modules.rag import models as _rag  # noqa: E402,F401
from modules.chat import models as _chat  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
