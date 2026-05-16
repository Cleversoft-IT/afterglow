"""Tiny JSONSchema → Pydantic v2 model converter.

Used by the Action Planner to turn an `ActionDefinition.payload_schema`
into a dynamic Pydantic model that we can hand to Google ADK as a typed
tool parameter. ADK introspects the annotation and emits a FunctionDeclaration
with typed parameters — Gemini then produces a structured JSON object
matching that shape rather than a free-form string.

Scope: covers the JSONSchema dialect actually used in our seed templates and
in the templates the wizard generates. NOT a general-purpose JSONSchema
implementation:

  - top-level must be `{"type": "object", "properties": {…}, "required": […]}`
  - property `type` is one of: string, integer, number, boolean, array, object
  - `array` items must be a scalar primitive or another object schema
  - `enum` is honoured for string properties via `Literal[...]`
  - `format` is decorative (we don't enforce date/time formats here — that's
    the action_executor's `jsonschema.validate` job)
  - $ref / oneOf / anyOf / allOf are NOT supported — the spike (Blocco 0a)
    confirmed plain shapes are enough for the v2 surface.

If the schema falls outside this dialect the converter raises
`JsonSchemaConversionError`; the Action Planner catches it and falls back to
a plain `dict` parameter (still validated by `jsonschema.validate` in the
executor before MOCK_REGISTRY is hit).
"""
from __future__ import annotations

import keyword
import re
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, create_model


class JsonSchemaConversionError(ValueError):
    pass


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")


def _safe_class_name(raw: str) -> str:
    """Return a Python-identifier-safe model name derived from `raw`.

    Action keys like `booking.create` cannot be used directly as a class
    name. We turn dots/dashes into underscores and PascalCase the result.
    """
    cleaned = _SAFE_NAME_RE.sub("_", raw).strip("_")
    if not cleaned:
        cleaned = "DynamicPayload"
    parts = [p for p in cleaned.split("_") if p]
    name = "".join(p[:1].upper() + p[1:] for p in parts) + "Payload"
    if keyword.iskeyword(name) or not name[0].isalpha():
        name = "_" + name
    return name


def _scalar_type(prop_schema: dict[str, Any]) -> Any:
    """Map a JSONSchema scalar type + optional enum to a Python type."""
    t = prop_schema.get("type")
    if t == "string":
        enum = prop_schema.get("enum")
        if enum and all(isinstance(v, str) for v in enum):
            return Literal[tuple(enum)]  # type: ignore[valid-type]
        return str
    if t == "integer":
        return int
    if t == "number":
        return float
    if t == "boolean":
        return bool
    raise JsonSchemaConversionError(f"unsupported scalar type: {t!r}")


def _property_type(prop_schema: dict[str, Any], parent_name: str, prop_name: str) -> Any:
    t = prop_schema.get("type")
    if t in ("string", "integer", "number", "boolean"):
        return _scalar_type(prop_schema)
    if t == "array":
        items = prop_schema.get("items") or {}
        items_t = items.get("type")
        if items_t == "object":
            inner = jsonschema_to_pydantic(
                items, name=f"{parent_name}_{prop_name}_item"
            )
            return list[inner]  # type: ignore[valid-type]
        if items_t in ("string", "integer", "number", "boolean"):
            return list[_scalar_type(items)]  # type: ignore[valid-type]
        raise JsonSchemaConversionError(
            f"unsupported array items.type: {items_t!r}"
        )
    if t == "object":
        return jsonschema_to_pydantic(
            prop_schema, name=f"{parent_name}_{prop_name}"
        )
    raise JsonSchemaConversionError(f"unsupported property type: {t!r}")


def jsonschema_to_pydantic(
    schema: dict[str, Any], *, name: str = "DynamicPayload"
) -> type[BaseModel]:
    """Build a Pydantic v2 model class from a JSONSchema object."""
    if not isinstance(schema, dict):
        raise JsonSchemaConversionError(f"schema is not a dict: {type(schema)}")
    if schema.get("type") != "object":
        raise JsonSchemaConversionError(
            f"top-level type must be 'object', got {schema.get('type')!r}"
        )

    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    additional_props = schema.get("additionalProperties", True)

    fields: dict[str, tuple[Any, Any]] = {}
    safe_name = _safe_class_name(name)

    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            raise JsonSchemaConversionError(
                f"property {prop_name!r} is not a dict"
            )
        py_type = _property_type(prop_schema, safe_name, prop_name)
        description = prop_schema.get("description")
        if prop_name in required:
            fields[prop_name] = (py_type, Field(..., description=description))
        else:
            fields[prop_name] = (
                Optional[py_type],
                Field(default=None, description=description),
            )

    config = ConfigDict(
        extra="forbid" if additional_props is False else "allow",
    )

    return create_model(  # type: ignore[no-any-return]
        safe_name,
        __config__=config,
        **fields,
    )
