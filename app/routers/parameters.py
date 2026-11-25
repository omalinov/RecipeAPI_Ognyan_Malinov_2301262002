import re
from typing import Annotated

from fastapi import Path
from pydantic import BeforeValidator

from app.schemas import SQLITE_MAX_INTEGER


def validate_integer_text(value: str) -> str:
    if not re.fullmatch(r"[+-]?[0-9]+", value):
        raise ValueError("Expected an integer.")
    return value


IntegerParameter = Annotated[int, BeforeValidator(validate_integer_text)]
ResourceId = Annotated[IntegerParameter, Path(gt=0, le=SQLITE_MAX_INTEGER)]
