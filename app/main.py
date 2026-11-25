from fastapi import FastAPI

app = FastAPI(
    title="Recipe Catalogue API",
    description="Manage recipes, authors, categories and ingredients.",
    redirect_slashes=False,
)
