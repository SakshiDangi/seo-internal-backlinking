import textwrap
from typing import Any, Dict, List, Optional, Type

import requests
from langchain_core.tools import StructuredTool

from pydantic.v1 import Field, BaseModel, create_model


def json_schema_to_pydantic(schema: Dict[str, Any], name: str, description: str) -> Type[BaseModel]:
    fields: Dict[str, Any] = {}

    for prop_name, prop_schema in schema.get("properties", {}).items():
        field_type = _get_field_type(prop_schema, prop_name)
        is_required = prop_name in schema.get("required", [])
        default = prop_schema.get("default", ... if is_required else None)

        field_info = Field(default=default)

        if "description" in prop_schema:
            field_info.description = prop_schema["description"]

        fields[prop_name] = (field_type, field_info)

    rtn = create_model(name, **fields)  # type: ignore

    rtn.__doc__ = textwrap.dedent(description)

    return rtn


def _get_field_type(prop_schema: Dict[str, Any], name="") -> Any:
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "null": None,
        "array": List,
        "object": Dict
    }

    if "type" not in prop_schema:
        return Any

    if prop_schema["type"] == "array":
        if "items" in prop_schema:
            item_type = _get_field_type(prop_schema["items"])
            return List[item_type]
        return List[Any]

    if prop_schema["type"] == "object":
        if "properties" in prop_schema:
            nested_fields = {
                k: (_get_field_type(v), Field(default=..., description=v.get("description")))
                for k, v in prop_schema["properties"].items()
            }
            return create_model(name.capitalize(), **nested_fields)
        return Dict[str, Any]

    if "enum" in prop_schema:
        from enum import Enum
        return Enum(
            f"{name.capitalize()}Enum",
            {str(v): v for v in prop_schema["enum"]}
        )

    field_type = type_mapping.get(prop_schema["type"], Any)

    if not prop_schema.get("required", True):
        return Optional[field_type]

    return field_type


def get_tools(input_tools):
    def update_nested_dict(d, path, value):
        keys = path.split('.')
        for key in keys[:-1]:
            if key.isdigit():
                key = int(key)
            d = d[key]
        final_key = keys[-1]
        if final_key.isdigit():
            final_key = int(final_key)
        d[final_key] = value
        return d

    def create_call_api_function(item):
        def call_api_function(**kwargs):
            """Call an API endpoint with the given URL and parameters, and return the JSON response."""
            data = item.dict()
            for key, value in kwargs.items():
                update_nested_dict(data, item.path[key], value)
            try:
                response = requests.request(
                    method=item.method,
                    url=item.api_url,
                    headers=data['headers'],
                    params= None if not data['params'] else  data['params'],
                    json = None if not data['body'] else data['body']
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                return {"Error": {e}}

        return call_api_function

    tools = []
    for item in input_tools:
        tool_schema = json_schema_to_pydantic(
            item.input_json_schema,
            name=item.name,
            description=item.description
        )
        tools.append(
            StructuredTool(
                func=create_call_api_function(item),
                name=item.name,
                description=item.description,
                args_schema=tool_schema
            )
        )
    return tools
