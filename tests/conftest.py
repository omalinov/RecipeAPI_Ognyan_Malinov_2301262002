from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.database import create_sqlite_engine, get_db
from app.main import app


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration_config():
    # A fresh directory avoids reusing a pytest temp folder owned by another account.
    with TemporaryDirectory(prefix="recipe-api-tests-") as directory:
        database_path = (Path(directory) / "catalogue.db").as_posix()
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
        yield config


@pytest.fixture
def database(migration_config):
    command.upgrade(migration_config, "head")
    engine = create_sqlite_engine(migration_config.get_main_option("sqlalchemy.url"))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(database):
    def override_db():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
