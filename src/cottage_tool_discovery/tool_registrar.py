from __future__ import annotations

import importlib.util
import inspect
import json
import re
from pathlib import Path
from typing import Any, get_args, get_origin, Union

from .util.db_path_config import read_tools_path


DOC_NAME_RE = re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.MULTILINE)
DOC_DESC_RE = re.compile(r"^\s*description\s*:\s*(.+?)\s*$", re.MULTILINE)


def load_module_from_path(path: str):
    path_obj = Path(path)
    spec = importlib.util.spec_from_file_location(path_obj.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_tool_metadata(docstring: str | None, fallback_name: str) -> tuple[str, str]:
    """
    Extract tool name and description from a docstring like:

    '''
    name: search_web
    description: search for current information from the web
    '''
    """
    docstring = docstring or ""

    name_match = DOC_NAME_RE.search(docstring)
    desc_match = DOC_DESC_RE.search(docstring)

    name = name_match.group(1).strip() if name_match else fallback_name
    description = desc_match.group(1).strip() if desc_match else ""
    return name, description


def python_type_to_schema(annotation: Any) -> dict[str, Any]:
    """
    Convert a subset of Python annotations into JSON Schema.
    Extend this as needed.
    """
    if annotation is inspect._empty:
        return {}

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Optional[T] or Union[T, None]
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        has_none = len(non_none) != len(args)

        if len(non_none) == 1 and has_none:
            schema = python_type_to_schema(non_none[0])
            # JSON Schema-style nullable
            if "type" in schema:
                schema["type"] = [schema["type"], "null"]
            else:
                schema = {"anyOf": [schema, {"type": "null"}]}
            return schema

        return {
            "anyOf": [python_type_to_schema(a) for a in args]
        }

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is Any:
        return {}

    if origin in (list,):
        item_schema = python_type_to_schema(args[0]) if args else {}
        return {
            "type": "array",
            "items": item_schema
        }

    if origin in (dict,):
        # Simple dict[str, T]
        value_schema = python_type_to_schema(args[1]) if len(args) == 2 else {}
        return {
            "type": "object",
            "additionalProperties": value_schema
        }

    # Fallback for unsupported/custom types
    return {}


def function_to_openai_tool(fn) -> dict[str, Any]:
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn)
    tool_name, description = parse_tool_metadata(doc, fn.__name__)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            raise ValueError(
                f"Unsupported parameter kind for {fn.__name__}: {param.kind}. "
                "Use named parameters for tool functions."
            )

        schema = python_type_to_schema(param.annotation)

        # Add default if present
        if param.default is not inspect._empty:
            schema["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = schema

    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def module_tools_from_file(path: str) -> list[dict[str, Any]]:
    module = load_module_from_path(path)
    tools = []

    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if obj.__module__ != module.__name__:
            continue

        if name.startswith("_"):
            continue

        tools.append(function_to_openai_tool(obj))

    return tools


def build_tools_from_files(file_path: str='') -> list[dict[str, Any]]:
    if not file_path:
        file_path = read_tools_path()
    tools_dir = Path(__file__).parent.parent / file_path
    tool_files = [str(p) for p in tools_dir.glob("*.py") if p.name != "__init__.py"]
    
    all_tools = []
    for path in tool_files:
        all_tools.extend(module_tools_from_file(path))
    return all_tools


if __name__ == "__main__":
    tools = build_tools_from_files()
    print(json.dumps(tools, indent=2))

