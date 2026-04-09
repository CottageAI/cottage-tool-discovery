from .tool_discovery import discover_tools
from .tool_registrar import build_tools_from_files
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cottage-tool-discovery")
except PackageNotFoundError:
    __version__ = "0.0.0"
    
__all__ = ["discover_tools", "build_tools_from_files"]
