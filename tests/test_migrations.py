from alembic import command
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.database import create_sqlite_engine


def test_fresh_upgrade(migration_config, database):
    assert set(inspect(database).get_table_names()) == {
        "alembic_version", "authors", "categories", "ingredients", "recipe_ingredients", "recipes",
    }
    columns = {column["name"]: column for column in inspect(database).get_columns("recipes")}
    assert columns["difficulty"]["nullable"] is False
    assert columns["difficulty"]["default"] is None
    with database.connect() as conn:
        assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0002"
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    command.check(migration_config)


def test_upgrade_and_downgrade_keep_existing_recipes_and_links(migration_config):
    command.upgrade(migration_config, "0001")
    engine = create_sqlite_engine(migration_config.get_main_option("sqlalchemy.url"))
    try:
        assert "difficulty" not in {col["name"] for col in inspect(engine).get_columns("recipes")}
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO authors (id, name, email, normalized_email) VALUES "
                "(1, 'Maria', 'maria@example.com', 'maria@example.com')"
            )
            conn.exec_driver_sql(
                "INSERT INTO categories (id, name, normalized_name) VALUES (2, 'Salads', 'salads')"
            )
            conn.exec_driver_sql(
                "INSERT INTO ingredients (id, name, normalized_name) VALUES (3, 'Tomato', 'tomato')"
            )
            conn.exec_driver_sql(
                "INSERT INTO recipes (id, title, normalized_title, instructions, preparation_time, "
                "servings, author_id, category_id) VALUES "
                "(4, 'Salad', 'salad', 'Slice and toss.', 15, 2, 1, 2), "
                "(5, 'Soup', 'soup', 'Simmer.', 25, 4, 1, NULL)"
            )
            conn.exec_driver_sql(
                "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES "
                "(4, 3, 2.5, 'pcs'), (5, 3, 300, 'g')"
            )

        command.upgrade(migration_config, "head")
        with engine.begin() as conn:
            assert conn.exec_driver_sql("SELECT id, difficulty FROM recipes ORDER BY id").all() == [
                (4, "easy"), (5, "easy"),
            ]
            conn.exec_driver_sql("UPDATE recipes SET difficulty = 'hard' WHERE id = 4")
        with engine.connect() as conn:
            for invalid in (None, "expert"):
                with pytest.raises(IntegrityError):
                    conn.exec_driver_sql("UPDATE recipes SET difficulty = ? WHERE id = 4", (invalid,))
                conn.rollback()

        for step in ("upgraded", "downgraded", "re-upgraded"):
            if step == "downgraded":
                command.downgrade(migration_config, "0001")
                assert "difficulty" not in {col["name"] for col in inspect(engine).get_columns("recipes")}
            elif step == "re-upgraded":
                command.upgrade(migration_config, "head")
            with engine.connect() as conn:
                assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
                assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
                assert conn.exec_driver_sql(
                    "SELECT id, title, instructions, preparation_time, servings, author_id, category_id "
                    "FROM recipes ORDER BY id"
                ).all() == [(4, "Salad", "Slice and toss.", 15, 2, 1, 2),
                            (5, "Soup", "Simmer.", 25, 4, 1, None)]
                assert conn.exec_driver_sql(
                    "SELECT recipe_id, ingredient_id, quantity, unit FROM recipe_ingredients ORDER BY recipe_id"
                ).all() == [(4, 3, 2.5, "pcs"), (5, 3, 300, "g")]
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT DISTINCT difficulty FROM recipes").all() == [("easy",)]
    finally:
        engine.dispose()
