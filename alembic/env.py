from alembic import context

from app.database import create_sqlite_engine
from app.models import Base


config = context.config


def run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        render_as_batch=True,
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Run migrations against a SQLite database.")
else:
    engine = create_sqlite_engine(config.get_main_option("sqlalchemy.url"))
    try:
        with engine.begin() as connection:
            # Explicit BEGIN makes SQLite DDL transactional in legacy transaction mode.
            connection.exec_driver_sql("BEGIN")
            run_migrations(connection)
    finally:
        engine.dispose()
