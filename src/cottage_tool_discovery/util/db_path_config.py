# util/tool_path_config.py  (or util/paths.py)

import json
from pathlib import Path
from platformdirs import user_config_dir

_APP = "Cottage_Tools_Discovery"
_FILE = "tool_path.json"

def config_file_path() -> Path:
    d = Path(user_config_dir(_APP))
    d.mkdir(parents=True, exist_ok=True)
    return d / _FILE

def write_tools_path(tool_path: str) -> None:
    p = Path(tool_path).expanduser().resolve()
    config_file_path().write_text(json.dumps({"tool_path": str(p)}), encoding="utf-8")

def read_tools_path() -> Path | None:
    f = config_file_path()
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    raw = data.get("tool_path")
    return Path(raw).expanduser().resolve() if raw else None
