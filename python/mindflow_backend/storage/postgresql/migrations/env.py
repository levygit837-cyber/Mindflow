import importlib.util
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from mindflow_backend.infra.config import get_settings

# Load Base directly from models.py to avoid triggering the broken storage/__init__.py chain
_models_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models.py"))
_spec = importlib.util.spec_from_file_location("_pg_models_direct", _models_path)
_models_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_models_mod)
Base = _models_mod.Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read DATABASE_URL from environment directly (avoids settings misconfiguration)
_db_url = os.environ.get("DATABASE_URL")
if not _db_url:
    settings = get_settings()
    _db_url = settings.database.url
# Alembic sync engine needs psycopg2 or psycopg (sync) driver
# postgresql+psycopg works fine for sync too
config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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
