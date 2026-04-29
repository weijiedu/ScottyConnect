"""
Decorator to validate request body against a Pydantic model.
"""
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec

from flask import jsonify, request
from pydantic import BaseModel, ValidationError

P = ParamSpec("P")


def validate(model: type[BaseModel]) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    def decorator(view: Callable[P, Any]) -> Callable[P, Any]:
        @wraps(view)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> Any:
            raw = request.get_json(silent=True)
            if raw is None:
                return jsonify({"message": "Invalid or missing JSON"}), 400

            try:
                body = model.model_validate(raw)
            except ValidationError as e:
                return jsonify({"errors": e.errors()}), 400

            return view(body, *args, **kwargs)

        return wrapped

    return decorator