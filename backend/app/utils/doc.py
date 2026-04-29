"""
Decorator utilities for OpenAPI metadata on Flask route handlers.
"""

from collections.abc import Callable
from typing import Any, ParamSpec

from pydantic import BaseModel

P = ParamSpec("P")

def doc(
    *,
    request: type[BaseModel] | None = None,
    response: type[BaseModel] | None = None,
    description: str = "",
    tags: list[str] | None = None,
    success_status: int = 200,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    def decorator(fn: Callable[P, Any]) -> Callable[P, Any]:
        fn._doc = {
            "request": request,
            "response": response,
            "description": description,
            "tags": tags or [],
            "success_status": str(success_status),
        }
        return fn

    return decorator
