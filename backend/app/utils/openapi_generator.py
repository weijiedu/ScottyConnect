"""
OpenAPI generator using route metadata from @doc decorators.
"""

from __future__ import annotations

from typing import Any

from flask import current_app

from app.utils.openapi_schema import add_model_to_components, model_ref


def _flask_rule_to_openapi_path(rule: str) -> str:
    return rule.replace("<", "{").replace(">", "}")


def build_operation(doc_meta: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    request_model_name = add_model_to_components(doc_meta.get("request"), components)
    response_model_name = add_model_to_components(doc_meta.get("response"), components)
    success_status = doc_meta.get("success_status", "200")

    operation: dict[str, Any] = {
        "summary": doc_meta.get("description", ""),
        "tags": doc_meta.get("tags", []),
        "responses": {
            success_status: {
                "description": "Success",
            }
        },
    }

    request_schema_ref = model_ref(request_model_name)
    if request_schema_ref is not None:
        operation["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": request_schema_ref}},
        }

    response_schema_ref = model_ref(response_model_name)
    if response_schema_ref is not None:
        operation["responses"][success_status]["content"] = {
            "application/json": {"schema": response_schema_ref}
        }

    return operation


def generate_openapi_spec() -> dict[str, Any]:
    paths: dict[str, dict[str, Any]] = {}
    components: dict[str, Any] = {}

    for rule in current_app.url_map.iter_rules():
        endpoint = current_app.view_functions[rule.endpoint]
        methods = rule.methods - {"HEAD", "OPTIONS"}

        doc_meta = getattr(endpoint, "_doc", None)
        if doc_meta is None:
            continue

        path = _flask_rule_to_openapi_path(rule.rule)
        paths.setdefault(path, {})

        for method in methods:
            paths[path][method.lower()] = build_operation(doc_meta, components)

    return {
        "openapi": "3.1.0",
        "info": {"title": "ScottyConnect API", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": components},
    }
