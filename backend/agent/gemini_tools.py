"""Gemini needs its own tool-schema shape, built from the same source of truth.

`TOOL_DEFINITIONS` in the registry is written once, in Anthropic's tool-use
format (name/description/input_schema). Gemini's FunctionDeclaration wants the
same information under `parameters`, with JSON Schema types replaced by its own
`Type` enum. Converting here means a new tool only ever needs writing once.
"""

from google.genai import types

_TYPE_MAP = {
    "string": types.Type.STRING,
    "integer": types.Type.INTEGER,
    "number": types.Type.NUMBER,
    "boolean": types.Type.BOOLEAN,
    "object": types.Type.OBJECT,
    "array": types.Type.ARRAY,
}


def _schema(node: dict) -> types.Schema:
    kind = node.get("type", "string")
    fields = {"type": _TYPE_MAP.get(kind, types.Type.STRING)}

    if "description" in node:
        fields["description"] = node["description"]
    if "enum" in node:
        fields["enum"] = node["enum"]

    if kind == "object" and "properties" in node:
        fields["properties"] = {
            name: _schema(prop) for name, prop in node["properties"].items()
        }
        if "required" in node:
            fields["required"] = node["required"]

    if kind == "array" and "items" in node:
        fields["items"] = _schema(node["items"])

    return types.Schema(**fields)


def to_function_declaration(tool_def: dict) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=tool_def["name"],
        description=tool_def["description"],
        parameters=_schema(tool_def["input_schema"]),
    )


def build_tools(tool_defs: list[dict]) -> list[types.Tool]:
    return [
        types.Tool(function_declarations=[to_function_declaration(t) for t in tool_defs])
    ]
