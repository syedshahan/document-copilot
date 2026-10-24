from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from alembic import context
from app.config import settings
from app.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ConfigParser treats percent signs in URL-encoded passwords as interpolation.
database_url = (
    make_url(str(settings.database_url))
    .set(drivername="postgresql+psycopg")
    .render_as_string(hide_password=False)
    .replace("%", "%%")
)
config.set_main_option("sqlalchemy.url", database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
