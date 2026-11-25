from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models import Difficulty, Unit


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SQLITE_MAX_INTEGER = 2**63 - 1
PositiveInteger = Annotated[int, Field(strict=True, gt=0, le=SQLITE_MAX_INTEGER)]
Quantity = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]


class AuthorFields(BaseModel):
    name: NonBlankText
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value):
        return value.strip() if isinstance(value, str) else value


class AuthorCreate(AuthorFields):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"name": "Maria Petrova", "email": "maria@example.com"}
    ]})


class AuthorUpdate(AuthorFields):
    pass


class AuthorResponse(AuthorFields):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CategoryCreate(BaseModel):
    name: NonBlankText = Field(examples=["Salads"])


class CategoryUpdate(CategoryCreate):
    pass


class CategoryResponse(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class IngredientCreate(BaseModel):
    name: NonBlankText = Field(examples=["Tomato"])


class IngredientUpdate(IngredientCreate):
    pass


class IngredientResponse(IngredientCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RecipeIngredientUpdate(BaseModel):
    quantity: Quantity = Field(examples=[2.5])
    unit: Unit = Field(examples=["pcs"])

    @field_validator("quantity", mode="before")
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("Quantity must be a number")
        return value


class RecipeIngredientCreate(RecipeIngredientUpdate):
    ingredient_id: PositiveInteger = Field(examples=[1])


class RecipeIngredientResponse(RecipeIngredientUpdate):
    model_config = ConfigDict(from_attributes=True)
    ingredient_id: int
    ingredient: IngredientResponse


class RecipeFields(BaseModel):
    title: NonBlankText = Field(examples=["Tomato Salad"])
    instructions: NonBlankText = Field(examples=["Slice the tomatoes and toss with salt."])
    preparation_time: PositiveInteger = Field(description="Preparation time in minutes", examples=[10])
    servings: PositiveInteger = Field(examples=[2])
    difficulty: Difficulty = Field(examples=["easy"])
    author_id: PositiveInteger = Field(examples=[1])
    category_id: PositiveInteger | None = Field(default=None, examples=[1])


class RecipeCreate(RecipeFields):
    pass


class RecipeUpdate(RecipeFields):
    pass


class RecipeResponse(RecipeFields):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ingredients: list[RecipeIngredientResponse]
