from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Unit(StrEnum):
    GRAMS = "g"
    MILLILITRES = "ml"
    PIECES = "pcs"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_author_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    normalized_email: Mapped[str] = mapped_column(Text, unique=True)
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="author", passive_deletes="all")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_category_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(Text, unique=True)
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="category", passive_deletes="all")


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_ingredient_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(Text, unique=True)
    recipe_links: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="ingredient", passive_deletes="all"
    )


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("author_id", "normalized_title", name="uq_recipe_author_title"),
        CheckConstraint("length(trim(title)) > 0", name="ck_recipe_title"),
        CheckConstraint("length(trim(instructions)) > 0", name="ck_recipe_instructions"),
        CheckConstraint(
            "typeof(preparation_time) = 'integer' AND preparation_time > 0",
            name="ck_recipe_preparation_time",
        ),
        CheckConstraint("typeof(servings) = 'integer' AND servings > 0", name="ck_recipe_servings"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)
    preparation_time: Mapped[int]
    servings: Mapped[int]
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(
            Difficulty,
            values_callable=lambda enum: [value.value for value in enum],
            native_enum=False,
            create_constraint=True,
            name="ck_recipe_difficulty",
        )
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id", ondelete="RESTRICT"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    author: Mapped[Author] = relationship(back_populates="recipes")
    category: Mapped[Category | None] = relationship(back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", passive_deletes="all", order_by="RecipeIngredient.ingredient_id"
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0 AND quantity <= 1.7976931348623157e308",
            name="ck_recipe_ingredient_quantity",
        ),
    )

    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), primary_key=True
    )
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[Unit] = mapped_column(
        Enum(Unit, values_callable=lambda enum: [value.value for value in enum],
             native_enum=False, create_constraint=True, name="ck_recipe_ingredient_unit")
    )
    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient] = relationship(back_populates="recipe_links")
