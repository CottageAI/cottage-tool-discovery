from __future__ import annotations

import importlib.util
import inspect
import re
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .util.db_path_config import read_tools_path


DOC_NAME_RE = re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.MULTILINE)
DOC_DESC_RE = re.compile(r"^\s*description\s*:\s*(.+?)\s*$", re.MULTILINE)


def load_module_from_path(path: Path) -> ModuleType:
    """
    Dynamically load a module from a .py file path.
    """
    spec = importlib.util.spec_from_file_location(f"tools.{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_tool_metadata(docstring: str | None) -> dict[str, str] | None:
    """
    Extract tool metadata from a docstring like:

    '''
    name: search_web
    description: search for current information from the web
    '''
    """
    if not docstring:
        return None

    name_match = DOC_NAME_RE.search(docstring)
    desc_match = DOC_DESC_RE.search(docstring)

    if not name_match or not desc_match:
        return None

    return {
        "name": name_match.group(1).strip(),
        "description": desc_match.group(1).strip(),
    }


def is_valid_tool_function(func: Callable[..., Any], module_name: str) -> bool:
    """
    A valid tool function:
    - is defined in the module itself
    - does not start with _
    - has both name: and description: in its docstring
    """
    if func.__module__ != module_name:
        return False

    if func.__name__.startswith("_"):
        return False

    metadata = parse_tool_metadata(inspect.getdoc(func))
    return metadata is not None


def discover_tools() -> dict[str, Callable[..., Any]]:
    """
    Discover all valid tool functions in the tools directory.

    Returns:
        {
            "tool_name": <function>,
            ...
        }
    """
    file_path = read_tools_path()
    if file_path is None:
        raise RuntimeError('User tools not initialized')
    tools_dir = Path(__file__).resolve().parent.parent / file_path

    discovered_tools: dict[str, Callable[..., Any]] = {}

    for path in sorted(tools_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue

        module = load_module_from_path(path)

        for _, func in inspect.getmembers(module, inspect.isfunction):
            if is_valid_tool_function(func, module.__name__):
                metadata = parse_tool_metadata(inspect.getdoc(func))
                tool_name = metadata["name"]

                if tool_name in discovered_tools:
                    raise ValueError(
                        f"Duplicate tool name discovered: {tool_name}"
                    )

                discovered_tools[tool_name] = func
    return discovered_tools

if __name__ == "__main__":
    tools = discover_tools()
    print(tools)
            