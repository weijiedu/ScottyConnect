"""
Helpers for converting Pydantic models into OpenAPI component schemas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def _rewrite_local_defs_refs(value: Any) -> Any:
    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str) and item.startswith("#/$defs/"):
                rewritten[key] = item.replace("#/$defs/", "#/components/schemas/")
            else:
                rewritten[key] = _rewrite_local_defs_refs(item)
        return rewritten

    if isinstance(value, list):
        return [_rewrite_local_defs_refs(item) for item in value]

    return value


def add_model_to_components(
    model: type[BaseModel] | None, components: dict[str, Any]
) -> str | None:
    if model is None:
        return None

    model_name = model.__name__
    if model_name in components:
        return model_name

    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    components[model_name] = _rewrite_local_defs_refs(schema)

    for def_name, def_schema in defs.items():
        components.setdefault(def_name, _rewrite_local_defs_refs(def_schema))

    return model_name


def model_ref(model_name: str | None) -> dict[str, str] | None:
    if model_name is None:
        return None
    return {"$ref": f"#/components/schemas/{model_name}"}
