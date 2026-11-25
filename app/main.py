from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import authors, categories, ingredients, recipes


app = FastAPI(
    title="Recipe Catalogue API",
    description="Manage recipes, authors, categories and ingredients.",
    redirect_slashes=False,
)

app.include_router(authors.router)
app.include_router(recipes.router)
app.include_router(categories.router)
app.include_router(ingredients.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Input can contain a nonfinite number that cannot be echoed in a JSON response.
    details = [
        {key: error[key] for key in ("loc", "msg", "type")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})
