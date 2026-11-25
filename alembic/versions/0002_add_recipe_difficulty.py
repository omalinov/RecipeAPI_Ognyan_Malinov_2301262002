"""Add required recipe difficulty and backfill existing recipes."""

from contextlib import contextmanager

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DIFFICULTY_CHECK = "ck_recipe_difficulty"


@contextmanager
def preserve_ingredient_links():
    # SQLite rebuilds recipes in batch mode. Dropping the old table would cascade
    # to its ingredient links, so keep the rows in a temporary table during the rebuild.
    op.execute(
        "CREATE TEMP TABLE migration_recipe_links AS "
        "SELECT recipe_id, ingredient_id, quantity, unit FROM recipe_ingredients"
    )
    op.execute("DELETE FROM recipe_ingredients")
    yield
    op.execute(
        "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) "
        "SELECT recipe_id, ingredient_id, quantity, unit FROM migration_recipe_links"
    )
    op.execute("DROP TABLE temp.migration_recipe_links")


def upgrade():
    op.add_column("recipes", sa.Column("difficulty", sa.String(6), nullable=True))
    op.execute("UPDATE recipes SET difficulty = 'easy'")
    with preserve_ingredient_links(), op.batch_alter_table("recipes") as batch:
        batch.alter_column("difficulty", existing_type=sa.String(6), nullable=False)
        batch.create_check_constraint(DIFFICULTY_CHECK, "difficulty IN ('easy', 'medium', 'hard')")


def downgrade():
    with preserve_ingredient_links(), op.batch_alter_table("recipes") as batch:
        batch.drop_constraint(DIFFICULTY_CHECK, type_="check")
        batch.drop_column("difficulty")
