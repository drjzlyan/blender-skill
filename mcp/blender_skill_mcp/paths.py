"""Path and configuration resolution shared by the MCP server and scripts.

Nothing in this repository hardcodes a user, machine, or install path. Every
location is derived from an environment variable or the platform's standard
config/data directories.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def data_home() -> Path:
    env = os.environ.get("BLENDER_SKILL_HOME")
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return (base / "blender-skill").resolve()


def config_home() -> Path:
    env = os.environ.get("BLENDER_SKILL_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return (base / "blender-skill" / "config.json").resolve()


def cache_home() -> Path:
    env = os.environ.get("BLENDER_SKILL_CACHE")
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return (base / "blender-skill").resolve()


def load_config() -> dict[str, Any]:
    path = config_home()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def save_config(data: dict[str, Any]) -> Path:
    path = config_home()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_config()
    existing.update(data)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def skill_root() -> Path:
    env = os.environ.get("BLENDER_SKILL_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    configured = load_config().get("skill_root")
    if configured:
        return Path(str(configured)).expanduser().resolve()
    # Running from a source checkout: mcp/blender_skill_mcp/paths.py -> repo root
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "SKILL.md").is_file():
        return candidate
    return data_home() / "skill"


def mcp_host() -> str:
    return os.environ.get("BLENDER_SKILL_MCP_HOST") or str(load_config().get("mcp_host") or "127.0.0.1")


def mcp_port() -> int:
    env = os.environ.get("BLENDER_SKILL_MCP_PORT")
    if env:
        try:
            return int(env)
        except ValueError:
            pass
    try:
        return int(load_config().get("mcp_port") or 9876)
    except (TypeError, ValueError):
        return 9876


def mcp_token() -> str:
    return os.environ.get("BLENDER_SKILL_MCP_TOKEN") or str(load_config().get("mcp_token") or "")


def model_dir() -> Path:
    env = os.environ.get("TRELLIS2_MODEL")
    if env:
        return Path(env).expanduser().resolve()
    configured = load_config().get("model_dir")
    if configured:
        return Path(str(configured)).expanduser().resolve()
    return data_home() / "models" / "TRELLIS.2-4B"


def trellis_python() -> Path | None:
    # Do not resolve symlinks: a venv's bin/python is a symlink and resolving it
    # loses the venv's site-packages (torch would appear missing).
    env = os.environ.get("TRELLIS2_PYTHON")
    if env:
        return Path(env).expanduser().absolute()
    configured = load_config().get("trellis_python")
    if configured:
        return Path(str(configured)).expanduser().absolute()
    candidate = data_home() / "venvs" / "trellis" / "bin" / "python"
    return candidate if candidate.is_file() else None


def trellis_vendor() -> Path:
    env = os.environ.get("TRELLIS2_VENDOR")
    if env:
        return Path(env).expanduser().resolve()
    configured = load_config().get("trellis_vendor")
    if configured:
        return Path(str(configured)).expanduser().resolve()
    return skill_root() / "trellis" / "vendor"


def bridge_script() -> Path:
    env = os.environ.get("TRELLIS2_BRIDGE")
    if env:
        return Path(env).expanduser().resolve()
    configured = load_config().get("trellis_bridge")
    if configured:
        return Path(str(configured)).expanduser().resolve()
    return skill_root() / "trellis" / "bridge" / "trellis2_bridge.py"


def outputs_dir() -> Path:
    env = os.environ.get("TRELLIS2_OUTPUT")
    if env:
        return Path(env).expanduser().resolve()
    configured = load_config().get("outputs_dir")
    if configured:
        return Path(str(configured)).expanduser().resolve()
    return data_home() / "outputs"


def mcp_executable() -> Path:
    configured = load_config().get("mcp_executable")
    if configured:
        return Path(str(configured)).expanduser().resolve()
    return data_home() / "venvs" / "mcp" / "bin" / "blender-skill-mcp"
