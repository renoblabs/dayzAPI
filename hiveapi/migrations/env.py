"""
Alembic environment script for DayZ HiveAPI.

This module configures Alembic for database migrations using SQLAlchemy models.
"""

import logging
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import Base from models and settings for DB_URL
from app.db.models import Base
from app.config import settings

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with value from settings
config.set_main_option("sqlalchemy.url", settings.DB_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set up logger for this module
logger = logging.getLogger("alembic.env")

# Add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()
        logger.info("Offline migrations completed")


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Handle special case for PostgreSQL - ensure extensions are created
    is_postgresql = settings.DB_URL.startswith("postgresql")
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # For PostgreSQL, create extensions if needed
        if is_postgresql:
            try:
                connection.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
                logger.info("Ensured pgcrypto extension is available")
            except Exception as e:
                logger.warning(f"Could not create pgcrypto extension: {e}")
        
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()
            logger.info("Online migrations completed")


# Execute migration based on context
if context.is_offline_mode():
    logger.info("Running migrations offline")
    run_migrations_offline()
else:
    logger.info("Running migrations online")
    run_migrations_online()
