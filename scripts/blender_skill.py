#!/usr/bin/env python3
"""blender-skill installer, doctor, and test runner.

Pure standard library so it runs before any virtual environment exists.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MIN_BLENDER = (4, 5, 0)
MIN_PYTHON = (3, 10)
TRELLIS_REPO = "microsoft/TRELLIS.2-4B"
TRELLIS_WEIGHTS_GB = 16.24
CUMESH_SHA = "12289e1062f0603f2f0d0771b02e1395d247f26f"
FLEXGEMM_SHA = "6dd94a859c26ee8246888502eada3dd8ad85532e"
UTILS3D_SHA = "9a4eb15e4021b67b12c460c7057d642626897ec8"
NVDIFFRAST_TAG = "v0.4.0"

AUX_MODELS = {
    "TRELLIS-image-large": {
        "repo": "microsoft/TRELLIS-image-large",
        "patterns": ["ckpts/ss_dec_conv3d_16l8_fp16.json", "ckpts/ss_dec_conv3d_16l8_fp16.safetensors"],
        "gated": False,
        "url": "https://huggingface.co/microsoft/TRELLIS-image-large",
    },
    "dinov3-vitl16": {
        "repo": "facebook/dinov3-vitl16-pretrain-lvd1689m",
        "patterns": ["*.json", "*.safetensors", "*.model", "*.txt", "*.py", "*.md"],
        "gated": True,
        "url": "https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m",
    },
    "RMBG-2.0": {
        "repo": "briaai/RMBG-2.0",
        "patterns": ["*.json", "*.safetensors", "*.py", "*.txt", "*.md"],
        "gated": True,
        "url": "https://huggingface.co/briaai/RMBG-2.0",
    },
}

SKIP_COPY = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "*.pyc",
    "*.pyo",
    ".venv",
    "venv",
    "outputs",
    "dist",
    "build",
    "*.egg-info",
}


# --------------------------------------------------------------------------- #
# process / platform helpers
# --------------------------------------------------------------------------- #

def run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None,
        timeout: float | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(command)}\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )
    return proc


def parse_version(text: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not match:
        return (0, 0, 0)
    return tuple(int(part) if part else 0 for part in match.groups())  # type: ignore[return-value]


def version_str(value: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in value)


def _blender_candidates() -> list[str]:
    candidates = []
    env = os.environ.get("BLENDER_BIN")
    if env:
        candidates.append(env)
    found = shutil.which("blender")
    if found:
        candidates.append(found)
    system = platform.system()
    if system == "Darwin":
        candidates.append("/Applications/Blender.app/Contents/MacOS/Blender")
    elif system == "Windows":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramW6432", r"C:\Program Files")):
            if base:
                candidates.extend(str(p) for p in Path(base).glob("Blender Foundation/Blender */blender.exe"))
    return [c for c in candidates if c]


def find_blender() -> dict[str, Any]:
    for candidate in _blender_candidates():
        path = Path(candidate).expanduser()
        if not path.is_file():
            continue
        proc = run([str(path), "--version"], timeout=30)
        version = parse_version(proc.stdout or proc.stderr)
        if version != (0, 0, 0):
            return {"found": True, "path": str(path), "version": version_str(version),
                    "version_tuple": version, "ok": version >= MIN_BLENDER}
    return {"found": False, "path": None, "version": None, "version_tuple": (0, 0, 0), "ok": False}


def _gpu_profile(vram: float) -> str:
    if vram >= 48:
        return "high"
    if vram >= 24:
        return "recommended"
    if vram >= 16:
        return "medium"
    if vram >= 8:
        return "low"
    return "minimal"


def _gpu_from_smi() -> dict[str, Any] | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    proc = run([exe, "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits"], timeout=15)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    parts = [p.strip() for p in proc.stdout.splitlines()[0].split(",")]
    if len(parts) < 2:
        return None
    try:
        vram = round(float(parts[1]) / 1024, 1)
    except ValueError:
        vram = 0.0
    return {"vendor": "nvidia", "name": parts[0], "vram_gb": vram,
            "driver": parts[2] if len(parts) > 2 else None,
            "profile": _gpu_profile(vram), "cuda": True, "source": "nvidia-smi"}


def _gpu_from_torch() -> dict[str, Any] | None:
    """nvidia-smi is not always on PATH (snap/IDE shells, containers). Ask the TRELLIS
    venv's torch instead: if it sees CUDA, TRELLIS can run, which is what this probe is for."""
    python = load_config().get("trellis_python") or str(paths_module().trellis_python())
    if not python or not Path(python).is_file():
        return None
    code = ("import json,torch;ok=torch.cuda.is_available();"
            "p=torch.cuda.get_device_properties(0) if ok else None;"
            "print(json.dumps({'ok':ok,'name':p.name if p else None,"
            "'vram':round(p.total_memory/2**30,1) if p else 0}))")
    proc = run([python, "-c", code], timeout=90)
    if proc.returncode != 0:
        return None
    try:
        info = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    if not info.get("ok"):
        return None
    vram = float(info["vram"])
    return {"vendor": "nvidia", "name": info["name"], "vram_gb": vram, "driver": None,
            "profile": _gpu_profile(vram), "cuda": True, "source": "torch"}


def gpu_info() -> dict[str, Any]:
    found = _gpu_from_smi() or _gpu_from_torch()
    if found:
        return found
    return {"vendor": None, "name": None, "vram_gb": 0.0, "driver": None,
            "profile": "mcp_only", "cuda": False,
            "note": "No NVIDIA GPU detected; manual Blender work works, TRELLIS.2 does not."}


def disk_info(path: Path | None = None) -> dict[str, Any]:
    target = path or Path.home()
    usage = shutil.disk_usage(target)
    free = round(usage.free / (1024 ** 3), 1)
    return {"path": str(target), "free_gb": free, "total_gb": round(usage.total / (1024 ** 3), 1),
            "ok_for_trellis": free >= 25}


def python_info() -> dict[str, Any]:
    version = sys.version_info[:3]
    return {"executable": sys.executable, "version": version_str(version),
            "ok": version >= MIN_PYTHON}


def port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, int(port)))
            return True
        except OSError:
            return False


def pick_port(host: str = "127.0.0.1", preferred: int = 9876) -> int:
    for port in range(preferred, preferred + 20):
        if port_available(host, port):
            return port
    raise RuntimeError(f"no free port in {preferred}-{preferred + 19}")


def blender_addons_dir(version: str) -> Path:
    major_minor = ".".join(version.split(".")[:2])
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Blender"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) / "Blender Foundation" / "Blender" if appdata else Path.home() / "AppData" / "Roaming" / "Blender Foundation" / "Blender"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
        base = base / "blender"
    return base / major_minor / "scripts" / "addons"


def blender_extensions_dir(version: str) -> Path:
    addons = blender_addons_dir(version)
    return addons.parents[1] / "extensions" / "user_default"


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #

def paths_module():
    sys.path.insert(0, str(ROOT / "mcp"))
    try:
        from blender_skill_mcp import paths as skill_paths  # type: ignore
        return skill_paths
    finally:
        sys.path.pop(0)


def load_config() -> dict[str, Any]:
    return paths_module().load_config()


def save_config(data: dict[str, Any]) -> Path:
    return paths_module().save_config(data)


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #

def doctor() -> dict[str, Any]:
    blender = find_blender()
    gpu = gpu_info()
    disk = disk_info()
    python = python_info()
    config = load_config()
    try:
        paths = paths_module()
        home = paths.data_home()
        mcp_bin = paths.mcp_executable()
        trellis_python = paths.trellis_python()
        model_dir = paths.model_dir()
        bridge = paths.bridge_script()
        vendor = paths.trellis_vendor()
    except Exception as exc:  # noqa: BLE001
        home = Path(os.environ.get("BLENDER_SKILL_HOME", Path.home() / ".local/share/blender-skill"))
        mcp_bin = home / "venvs" / "mcp" / "bin" / "blender-skill-mcp"
        trellis_python = None
        model_dir = home / "models" / "TRELLIS.2-4B"
        bridge = ROOT / "trellis" / "bridge" / "trellis2_bridge.py"
        vendor = ROOT / "trellis" / "vendor"
        config = {"error": str(exc)}
    aux_dir = Path(str(config.get("aux_dir") or (model_dir / "aux")))
    aux = {
        "aux_dir": str(aux_dir),
        "sparse_structure_decoder": (aux_dir / "TRELLIS-image-large" / "ckpts" / "ss_dec_conv3d_16l8_fp16.safetensors").is_file(),
        "dinov3": (aux_dir / "dinov3-vitl16" / "config.json").is_file(),
        "rmbg": (aux_dir / "RMBG-2.0" / "config.json").is_file(),
    }
    addons = blender_addons_dir(blender["version"]) if blender["found"] else None
    addon_dir = addons / "blender_skill_mcp" if addons else None
    local_paths = locals().get("paths")
    config_path = str(local_paths.config_home()) if local_paths is not None else ""
    report = {
        "ok": bool(blender["ok"] and python["ok"] and mcp_bin.is_file()),
        "blender": {**blender, "version_tuple": list(blender["version_tuple"])},
        "python": python,
        "gpu": gpu,
        "disk": disk,
        "paths": {
            "repo": str(ROOT),
            "home": str(home),
            "config": config_path,
            "mcp_executable": str(mcp_bin),
            "mcp_executable_present": mcp_bin.is_file(),
            "trellis_python": str(trellis_python) if trellis_python else None,
            "trellis_python_present": bool(trellis_python and Path(trellis_python).is_file()),
            "trellis_vendor": str(vendor),
            "trellis_vendor_present": (vendor / "trellis2").is_dir(),
            "trellis_bridge": str(bridge),
            "trellis_bridge_present": bridge.is_file(),
            "model_dir": str(model_dir),
            "model_present": (model_dir / "pipeline.json").is_file(),
            "aux": aux,
        },
        "addon": {
            "path": str(addon_dir) if addon_dir else None,
            "present": bool(addon_dir and addon_dir.is_dir()),
        },
        "config": config,
        "warnings": [],
        "errors": [],
    }
    if not blender["found"]:
        report["errors"].append("Blender not found. Install Blender 4.5+ or set BLENDER_BIN.")
    elif not blender["ok"]:
        report["errors"].append(f"Blender {blender['version']} is older than 4.5.")
    if not python["ok"]:
        report["errors"].append(f"Python {python['version']} is older than 3.10.")
    if not mcp_bin.is_file():
        report["warnings"].append("MCP venv not installed. Run setup.")
    if not report["addon"]["present"]:
        report["warnings"].append("Blender add-on not installed. Run setup.")
    if gpu["profile"] == "mcp_only":
        report["warnings"].append("No NVIDIA GPU: TRELLIS.2 unavailable; MCP/manual Blender unaffected.")
    elif gpu["profile"] in {"minimal", "low"}:
        report["warnings"].append(
            f"{gpu['vram_gb']} GB VRAM: generation may be slow or run out of memory. Use 512/low-VRAM."
        )
    elif gpu["profile"] == "medium":
        report["warnings"].append(
            f"{gpu['vram_gb']} GB VRAM: prefer 1024 with low-VRAM; 1024_cascade may OOM."
        )
    if not disk["ok_for_trellis"]:
        report["warnings"].append(f"Only {disk['free_gb']} GB free; a fresh TRELLIS setup needs ~25 GB.")
    report["trellis_ok"] = bool(
        report["paths"]["trellis_python_present"]
        and report["paths"]["trellis_vendor_present"]
        and report["paths"]["trellis_bridge_present"]
        and report["paths"]["model_present"]
        and aux["sparse_structure_decoder"]
        and aux["dinov3"]
    )
    if report["paths"]["model_present"] and not aux["sparse_structure_decoder"]:
        report["warnings"].append("Sparse-structure decoder missing; run: trellis download")
    if report["paths"]["model_present"] and not aux["dinov3"]:
        report["warnings"].append(
            "DINOv3 conditioner missing (gated). Accept the license, set HF_TOKEN, then run: trellis download"
        )
    if report["paths"]["model_present"] and not aux["rmbg"]:
        report["warnings"].append("RMBG-2.0 missing (gated, optional); alpha input or BiRefNet fallback will be used.")
    return report


# --------------------------------------------------------------------------- #
# skill installation
# --------------------------------------------------------------------------- #

def harness_targets(harness: str) -> list[tuple[str, Path]]:
    home = Path.home()
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    mapping: dict[str, list[Path]] = {
        "opencode": [xdg_config / "opencode" / "skills"],
        "claude": [home / ".claude" / "skills"],
        "codex": [home / ".codex" / "skills", home / ".agents" / "skills"],
        "cursor": [home / ".cursor" / "skills"],
        "agents": [home / ".agents" / "skills"],
        "generic": [home / ".agents" / "skills"],
    }
    if harness == "all":
        seen: set[Path] = set()
        result: list[tuple[str, Path]] = []
        for name in ("opencode", "claude", "codex", "cursor", "agents"):
            for path in mapping[name]:
                if path not in seen:
                    seen.add(path)
                    result.append((name, path))
        return result
    return [(harness, path) for path in mapping[harness]]


def detect_harness() -> str:
    home = Path.home()
    if (home / ".config" / "opencode").is_dir():
        return "opencode"
    if (home / ".claude").is_dir():
        return "claude"
    if (home / ".codex").is_dir():
        return "codex"
    if (home / ".cursor").is_dir():
        return "cursor"
    return "agents"


def _ignore(_dir: str, names: list[str]) -> set[str]:
    import fnmatch
    ignored = set()
    for name in names:
        if any(fnmatch.fnmatch(name, pattern) for pattern in SKIP_COPY):
            ignored.add(name)
        elif any(name.endswith(suffix) for suffix in (".pyc", ".pyo")):
            ignored.add(name)
    return ignored


def install_skill(harness: str, *, project: Path | None = None, force: bool = False) -> dict[str, Any]:
    installed: list[str] = []
    if harness == "auto":
        harness = detect_harness()
    targets = harness_targets(harness)
    if project is not None:
        targets = [(harness, project / f".{harness}" / "skills")]
    for name, skills_dir in targets:
        skills_dir.mkdir(parents=True, exist_ok=True)
        dest = skills_dir / "blender-skill"
        if dest.resolve() == ROOT.resolve():
            installed.append(str(dest))
            continue
        if dest.exists():
            if not force:
                backup = dest.with_name(f"blender-skill.bak-{int(time.time())}")
                dest.rename(backup)
            else:
                shutil.rmtree(dest)
        shutil.copytree(ROOT, dest, ignore=_ignore)
        installed.append(str(dest))
    return {"harness": harness, "installed": installed}


def mcp_entry(skill_root: Path, mcp_bin: Path, port: int, token: str) -> dict[str, Any]:
    paths = paths_module()
    return {
        "type": "local",
        "command": [str(mcp_bin)],
        "enabled": True,
        "environment": {
            "BLENDER_SKILL_HOME": str(paths.data_home()),
            "BLENDER_SKILL_CONFIG": str(paths.config_home()),
            "BLENDER_SKILL_ROOT": str(skill_root),
            "BLENDER_SKILL_MCP_PORT": str(port),
            "BLENDER_SKILL_MCP_TOKEN": token,
        },
    }


def _strip_jsonc(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    escape = False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            i += 1
            continue
        if text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
            continue
        out.append(char)
        i += 1
    cleaned = "".join(out)
    return re.sub(r",\s*([}\]])", r"\1", cleaned)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(_strip_jsonc(text))
        return data if isinstance(data, dict) else {}
    except Exception:
        backup = path.with_name(path.name + f".bak-{int(time.time())}")
        path.rename(backup)
        return {}


def configure_harnesses(harness: str, skill_root: Path, mcp_bin: Path, port: int, token: str,
                        *, project: Path | None = None) -> dict[str, Any]:
    home = Path.home()
    xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    entry = mcp_entry(skill_root, mcp_bin, port, token)
    changed: list[str] = []
    if harness == "auto":
        harness = detect_harness()
    names = ["opencode", "claude", "codex", "cursor", "agents"] if harness == "all" else [harness]
    for name in names:
        if name == "opencode":
            path = xdg_config / "opencode" / "opencode.jsonc"
            if not path.exists() and (xdg_config / "opencode" / "opencode.json").exists():
                path = xdg_config / "opencode" / "opencode.json"
            data = _read_json(path)
            mcp = data.setdefault("mcp", {})
            mcp["blender-skill"] = entry
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            changed.append(str(path))
        elif name == "claude":
            path = home / ".claude.json"
            data = _read_json(path)
            servers = data.setdefault("mcpServers", {})
            servers["blender-skill"] = {k: v for k, v in entry.items() if k != "type"}
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            changed.append(str(path))
            if project is not None:
                ppath = project / ".mcp.json"
                pdata = _read_json(ppath)
                pdata.setdefault("mcpServers", {})["blender-skill"] = {k: v for k, v in entry.items() if k != "type"}
                ppath.write_text(json.dumps(pdata, indent=2) + "\n", encoding="utf-8")
                changed.append(str(ppath))
        elif name == "codex":
            path = home / ".codex" / "config.toml"
            path.parent.mkdir(parents=True, exist_ok=True)
            _write_codex_block(path, entry)
            changed.append(str(path))
        elif name == "cursor":
            path = home / ".cursor" / "mcp.json"
            data = _read_json(path)
            data.setdefault("mcpServers", {})["blender-skill"] = {k: v for k, v in entry.items() if k != "type"}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            changed.append(str(path))
        elif name == "agents":
            path = xdg_config / "blender-skill" / "adapters" / "mcp.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"mcpServers": {"blender-skill": entry}}, indent=2) + "\n", encoding="utf-8")
            changed.append(str(path))
    return {"harness": harness, "changed": changed, "entry": entry}


def _write_codex_block(path: Path, entry: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    start = text.find("[mcp_servers.blender-skill]")
    if start != -1:
        end = text.find("\n[", start + 1)
        text = text[:start] + (text[end + 1:] if end != -1 else "")
    env = entry.get("environment", {})
    lines = ["[mcp_servers.blender-skill]"]
    lines.append(f"command = {json.dumps(entry['command'][0])}")
    lines.append("args = []")
    lines.append("")
    lines.append("[mcp_servers.blender-skill.env]")
    for key, value in env.items():
        lines.append(f"{key} = {json.dumps(str(value))}")
    path.write_text(text.rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# MCP / add-on setup
# --------------------------------------------------------------------------- #

def install_mcp_venv(home: Path) -> dict[str, Any]:
    venv = home / "venvs" / "mcp"
    python = venv / "bin" / "python"
    if not python.is_file():
        uv = shutil.which("uv")
        venv.parent.mkdir(parents=True, exist_ok=True)
        if uv:
            run([uv, "venv", "--python", "3.11", str(venv)], check=True)
        else:
            run([sys.executable, "-m", "venv", str(venv)], check=True)
    if not python.is_file():
        raise RuntimeError(f"failed to create MCP venv at {venv}")
    uv = shutil.which("uv")
    if uv:
        run([uv, "pip", "install", "--python", str(python), "-e", str(ROOT / "mcp")], check=True)
    else:
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        run([str(python), "-m", "pip", "install", "-e", str(ROOT / "mcp")], check=True)
    executable = venv / "bin" / "blender-skill-mcp"
    if not executable.is_file():
        raise RuntimeError("blender-skill-mcp entry point missing after install")
    return {"venv": str(venv), "executable": str(executable)}


def install_addon(blender: dict[str, Any], host: str, port: int, token: str) -> dict[str, Any]:
    if not blender.get("found"):
        return {"ok": False, "error": "Blender not found"}
    version = blender["version"]
    source = ROOT / "blender_addon" / "blender_skill_mcp"
    addons = blender_addons_dir(version)
    target = addons / "blender_skill_mcp"
    addons.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = f"""
import bpy, sys
module = "blender_skill_mcp"
try:
    bpy.ops.preferences.addon_enable(module=module)
except Exception as exc:
    print("ENABLE_FAILED", exc)
    sys.exit(1)
try:
    prefs = bpy.context.preferences.addons[module].preferences
    prefs.host = {host!r}
    prefs.port = {int(port)}
    prefs.token = {token!r}
    prefs.auto_start = True
    bpy.ops.wm.save_userpref()
except Exception as exc:
    print("PREFS_FAILED", exc)
    sys.exit(1)
print("ADDON_OK")
"""
    proc = run([blender["path"], "--background", "--python-expr", code], timeout=180)
    output = (proc.stdout or "") + (proc.stderr or "")
    ok = "ADDON_OK" in output and proc.returncode == 0
    if ok:
        return {"ok": True, "path": str(target), "enabled": True, "output": output[-2000:]}
    # Fallback: install as a Blender extension directory.
    ext = blender_extensions_dir(version) / "blender_skill_mcp"
    ext.parent.mkdir(parents=True, exist_ok=True)
    if ext.exists():
        shutil.rmtree(ext)
    shutil.copytree(source, ext, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code_ext = f"""
import bpy, sys
module = "bl_ext.user_default.blender_skill_mcp"
try:
    bpy.ops.preferences.addon_enable(module=module)
except Exception as exc:
    print("ENABLE_FAILED", exc)
    sys.exit(1)
try:
    prefs = bpy.context.preferences.addons[module].preferences
    prefs.host = {host!r}
    prefs.port = {int(port)}
    prefs.token = {token!r}
    prefs.auto_start = True
    bpy.ops.wm.save_userpref()
except Exception as exc:
    print("PREFS_FAILED", exc)
    sys.exit(1)
print("ADDON_OK")
"""
    proc = run([blender["path"], "--background", "--python-expr", code_ext], timeout=180)
    output = (proc.stdout or "") + (proc.stderr or "")
    return {"ok": "ADDON_OK" in output and proc.returncode == 0, "path": str(ext),
            "enabled": "ADDON_OK" in output, "output": output[-2000:]}


def install_trellis_addon(blender: dict[str, Any], *, vendor: Path, python: Path,
                           model_dir: Path, output_dir: Path) -> dict[str, Any]:
    if not blender.get("found"):
        return {"ok": False, "error": "Blender not found"}
    source = ROOT / "trellis" / "addon" / "blender_addon"
    target = blender_addons_dir(blender["version"]) / "trellis2_bridge"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = f"""
import bpy, sys
module = "trellis2_bridge"
try:
    bpy.ops.preferences.addon_enable(module=module)
except Exception as exc:
    print("ENABLE_FAILED", exc)
    sys.exit(1)
try:
    prefs = bpy.context.preferences.addons[module].preferences
    prefs.vendor_dir = {str(vendor)!r}
    prefs.python_executable = {str(python)!r}
    prefs.output_dir = {str(output_dir)!r}
    prefs.model = {str(model_dir)!r}
    prefs.attn_backend = "sdpa"
    prefs.low_vram = True
    bpy.ops.wm.save_userpref()
except Exception as exc:
    print("PREFS_FAILED", exc)
    sys.exit(1)
print("TRELLIS_ADDON_OK")
"""
    proc = run([blender["path"], "--background", "--python-expr", code], timeout=180)
    output = (proc.stdout or "") + (proc.stderr or "")
    return {"ok": "TRELLIS_ADDON_OK" in output and proc.returncode == 0,
            "path": str(target), "output": output[-2000:]}


# --------------------------------------------------------------------------- #
# TRELLIS.2 setup
# --------------------------------------------------------------------------- #

def clean_vendor_build(vendor: Path) -> None:
    """Remove in-tree build artifacts so the installed skill stays small."""
    import shutil as _shutil
    for pattern in ("build", "*.egg-info", "__pycache__"):
        for path in list(vendor.rglob(pattern)):
            if path.is_dir():
                _shutil.rmtree(path, ignore_errors=True)
    for path in vendor.rglob("*.so"):
        if "third_party" not in str(path):
            try:
                path.unlink()
            except OSError:
                pass
    for path in vendor.rglob("*.pyc"):
        try:
            path.unlink()
        except OSError:
            pass


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")


def _pip(python: Path, args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    uv = shutil.which("uv")
    if uv:
        return run([uv, "pip", "install", "--python", str(python), *args], timeout=timeout)
    return run([str(python), "-m", "pip", "install", *args], timeout=timeout)


def setup_trellis(home: Path, *, with_flash_attn: bool = False, python_override: str | None = None,
                  skip_build: bool = False, vendor_root: Path | None = None) -> dict[str, Any]:
    if python_override:
        python = Path(python_override).expanduser().absolute()
        if not python.is_file():
            return {"ok": False, "error": f"TRELLIS python not found: {python}"}
        check = run([str(python), "-c", "import torch; print(torch.__version__, torch.cuda.is_available())"], timeout=60)
        if check.returncode != 0:
            return {"ok": False, "error": "torch is not importable in the supplied TRELLIS python",
                    "output": (check.stdout + check.stderr)[-2000:]}
        return {"ok": True, "python": str(python), "reused": True,
                "torch": (check.stdout or "").strip()}
    venv = home / "venvs" / "trellis"
    python = _venv_python(venv)
    if not python.is_file():
        uv = shutil.which("uv")
        venv.parent.mkdir(parents=True, exist_ok=True)
        if uv:
            proc = run([uv, "venv", "--python", "3.10", "--python-preference", "only-managed", str(venv)], timeout=900)
            if proc.returncode != 0:
                proc = run([uv, "venv", "--python", "3.10", str(venv)], timeout=900)
            if proc.returncode != 0:
                return {"ok": False, "error": "failed to create Python 3.10 venv", "output": (proc.stdout + proc.stderr)[-3000:]}
        else:
            proc = run([sys.executable, "-m", "venv", str(venv)], timeout=300)
            if proc.returncode != 0:
                return {"ok": False, "error": "failed to create TRELLIS venv", "output": (proc.stdout + proc.stderr)[-3000:]}
    if skip_build:
        return {"ok": python.is_file(), "python": str(python), "skipped": True}
    verify_code = "import torch, cumesh, flex_gemm, nvdiffrast, o_voxel; "
    if not with_flash_attn:
        verify_code += "import xformers; "
    verify_code += "print('TORCH', torch.__version__, torch.cuda.is_available())"
    verify = run([str(python), "-c", verify_code], timeout=180)
    if verify.returncode == 0 and not with_flash_attn:
        return {"ok": True, "python": str(python), "reused_env": True,
                "verify": (verify.stdout or "").strip()}
    steps: list[dict[str, Any]] = []

    def step(name: str, args: list[str], timeout: float = 3600) -> bool:
        proc = _pip(python, args, timeout=timeout)
        steps.append({"step": name, "returncode": proc.returncode,
                      "tail": ((proc.stdout or "") + (proc.stderr or ""))[-2500:]})
        if proc.returncode != 0:
            raise RuntimeError(f"{name} failed")
        return True

    try:
        step("torch", ["torch==2.6.0", "torchvision==0.21.0",
                       "--index-url", "https://download.pytorch.org/whl/cu124"], timeout=3600)
        step("base", [
            "setuptools", "wheel", "packaging", "pip",
            "numpy<2", "pillow", "imageio", "imageio-ffmpeg", "tqdm", "easydict",
            "opencv-python-headless", "ninja", "trimesh", "transformers", "safetensors",
            "huggingface_hub", "zstandard", "plyfile", "kornia", "timm",
        ], timeout=3600)
        step("utils3d", [f"git+https://github.com/EasternJournalist/utils3d.git@{UTILS3D_SHA}"], timeout=1800)
        if not with_flash_attn:
            step("xformers", ["xformers==0.0.29.post2", "--no-deps"], timeout=1800)
        vendor = vendor_root or (ROOT / "trellis" / "vendor")
        step("cumesh", [str(vendor / "CuMesh"), "--no-build-isolation"], timeout=3600)
        step("flexgemm", [str(vendor / "FlexGEMM"), "--no-build-isolation"], timeout=3600)
        step("nvdiffrast", [f"git+https://github.com/NVlabs/nvdiffrast.git@{NVDIFFRAST_TAG}",
                            "--no-build-isolation"], timeout=3600)
        step("o-voxel", [str((vendor_root or (ROOT / "trellis" / "vendor")) / "o-voxel"),
                         "--no-deps", "--no-build-isolation"], timeout=3600)
        if with_flash_attn:
            step("flash-attn", ["flash-attn==2.7.3", "--no-build-isolation"], timeout=7200)
        verify = run([str(python), "-c", (
            "import torch, cumesh, flex_gemm, nvdiffrast, o_voxel; "
            "print('TORCH', torch.__version__, torch.cuda.is_available())"
        )], timeout=180)
        clean_vendor_build(vendor_root or (ROOT / "trellis" / "vendor"))
        return {"ok": verify.returncode == 0, "python": str(python), "steps": steps,
                "verify": ((verify.stdout or "") + (verify.stderr or ""))[-3000:]}
    except Exception as exc:  # noqa: BLE001
        clean_vendor_build(vendor_root or (ROOT / "trellis" / "vendor"))
        return {"ok": False, "python": str(python), "error": str(exc), "steps": steps}


def download_weights(python: Path, model_dir: Path) -> dict[str, Any]:
    if (model_dir / "pipeline.json").is_file() and any(model_dir.glob("ckpts/*.safetensors")):
        return {"ok": True, "model_dir": str(model_dir), "skipped": True}
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    code = (
        "from huggingface_hub import snapshot_download\n"
        f"snapshot_download(repo_id={TRELLIS_REPO!r}, local_dir={str(model_dir)!r}, "
        "allow_patterns=['*.json','*.safetensors','README.md','.gitattributes'], max_workers=4)\n"
        "print('WEIGHTS_OK')\n"
    )
    proc = run([str(python), "-c", code], timeout=7200)
    ok = "WEIGHTS_OK" in (proc.stdout or "") and proc.returncode == 0
    return {"ok": ok, "model_dir": str(model_dir),
            "output": ((proc.stdout or "") + (proc.stderr or ""))[-3000:]}


def download_aux_models(python: Path, model_dir: Path, *, aux_dir: Path | None = None) -> dict[str, Any]:
    """Download the auxiliary checkpoints TRELLIS.2 loads in addition to 4B weights."""
    aux_dir = aux_dir or (model_dir / "aux")
    aux_dir.mkdir(parents=True, exist_ok=True)
    specs = {name: spec for name, spec in AUX_MODELS.items()}
    payload = {"model_dir": str(model_dir), "aux_dir": str(aux_dir), "specs": specs}
    code = (
        "import json, os\n"
        "from pathlib import Path\n"
        "from huggingface_hub import snapshot_download\n"
        f"payload = {payload!r}\n"
        "result = {'ok': True, 'downloaded': [], 'gated': [], 'errors': []}\n"
        "token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN') or None\n"
        "for name, spec in payload['specs'].items():\n"
        "    dest = Path(payload['aux_dir']) / name\n"
        "    try:\n"
        "        snapshot_download(repo_id=spec['repo'], local_dir=str(dest), allow_patterns=spec['patterns'], token=token)\n"
        "        result['downloaded'].append({'name': name, 'path': str(dest), 'repo': spec['repo']})\n"
        "    except Exception as exc:\n"
        "        text = str(exc)\n"
        "        if 'gated' in text.lower() or '401' in text or '403' in text or 'restricted' in text.lower():\n"
        "            result['gated'].append({'name': name, 'repo': spec['repo'], 'url': spec['url'], 'error': text[:500]})\n"
        "        else:\n"
        "            result['errors'].append({'name': name, 'repo': spec['repo'], 'error': text[:500]})\n"
        "result['ok'] = not result['errors'] and not result['gated']\n"
        "print('AUX_RESULT ' + json.dumps(result))\n"
    )
    proc = run([str(python), "-c", code], timeout=3600)
    result: dict[str, Any] = {}
    for line in (proc.stdout or "").splitlines():
        if line.startswith("AUX_RESULT "):
            try:
                result = json.loads(line[len("AUX_RESULT "):])
            except Exception:
                result = {}
            break
    if not result:
        result = {"ok": False, "error": "aux download produced no result",
                  "output": ((proc.stdout or "") + (proc.stderr or ""))[-3000:]}
    return result


def rewrite_pipeline_paths(model_dir: Path, aux_dir: Path | None = None) -> dict[str, Any]:
    """Point pipeline configs at local aux checkpoints when they exist."""
    aux_dir = aux_dir or (model_dir / "aux")
    changed = []
    for name in ("pipeline.json", "texturing_pipeline.json"):
        path = model_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        args = data.setdefault("args", {})
        models = args.get("models", {})
        original = json.dumps(data, sort_keys=True)
        ss_dec = aux_dir / "TRELLIS-image-large" / "ckpts" / "ss_dec_conv3d_16l8_fp16"
        if "sparse_structure_decoder" in models and (Path(str(ss_dec) + ".json").is_file() or (ss_dec.with_suffix(".json")).is_file()):
            models["sparse_structure_decoder"] = "aux/TRELLIS-image-large/ckpts/ss_dec_conv3d_16l8_fp16"
        dino = aux_dir / "dinov3-vitl16"
        if "image_cond_model" in args and (dino / "config.json").is_file():
            args["image_cond_model"].setdefault("args", {})["model_name"] = str(dino)
        rmbg = aux_dir / "RMBG-2.0"
        if "rembg_model" in args and (rmbg / "config.json").is_file():
            args["rembg_model"].setdefault("args", {})["model_name"] = str(rmbg)
        new = json.dumps(data, indent=4)
        if json.dumps(data, sort_keys=True) != original:
            backup = path.with_suffix(path.suffix + ".orig")
            if not backup.exists():
                backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            path.write_text(new + "\n", encoding="utf-8")
            changed.append(name)
    return {"changed": changed, "aux_dir": str(aux_dir)}


# --------------------------------------------------------------------------- #
# TRELLIS bridge wrapper
# --------------------------------------------------------------------------- #

def download_all(python: Path, model_dir: Path, *, aux_dir: Path | None = None) -> dict[str, Any]:
    main = download_weights(python, model_dir)
    aux = download_aux_models(python, model_dir, aux_dir=aux_dir)
    rewrite = rewrite_pipeline_paths(model_dir, aux_dir=aux_dir)
    return {"ok": bool(main.get("ok")) and bool(aux.get("ok")), "weights": main, "aux": aux, "pipeline": rewrite}


def trellis_command(args: list[str]) -> list[str]:
    config = load_config()
    python = config.get("trellis_python")
    if not python or not Path(python).is_file():
        raise SystemExit("TRELLIS python missing; run: python3 scripts/blender_skill.py setup")
    bridge = Path(config.get("trellis_bridge") or (ROOT / "trellis" / "bridge" / "trellis2_bridge.py"))
    vendor = Path(config.get("trellis_vendor") or (ROOT / "trellis" / "vendor"))
    model = Path(config.get("model_dir") or (ROOT / "models" / "TRELLIS.2-4B"))
    env = os.environ.copy()
    env.setdefault("ATTN_BACKEND", str(config.get("attn_backend") or "sdpa"))
    env["TRELLIS2_VENDOR"] = str(vendor)
    env["TRELLIS2_MODEL"] = str(model)
    command = [str(python), str(bridge), "--vendor-dir", str(vendor), "--model", str(model), *args]
    return command, env  # type: ignore[return-value]


def run_trellis(args: list[str], timeout: float = 3600) -> int:
    command, env = trellis_command(args)
    return subprocess.call(command, env=env, cwd=str(ROOT))


# --------------------------------------------------------------------------- #
# setup orchestration
# --------------------------------------------------------------------------- #

def setup(args: argparse.Namespace) -> dict[str, Any]:
    report: dict[str, Any] = {"steps": [], "warnings": [], "errors": []}
    blender = find_blender()
    gpu = gpu_info()
    disk = disk_info()
    if not blender["found"]:
        report["errors"].append("Blender not found. Install Blender 4.5+ or set BLENDER_BIN.")
        return report
    if not blender["ok"]:
        report["errors"].append(f"Blender {blender['version']} is older than 4.5.")
        return report
    if not python_info()["ok"]:
        report["errors"].append(f"Python {sys.version_info[:3]} is older than 3.10.")
        return report
    if gpu["profile"] == "mcp_only":
        report["warnings"].append("No NVIDIA GPU: TRELLIS will not run. MCP and manual Blender still work.")
    elif gpu["profile"] in {"minimal", "low", "medium"}:
        report["warnings"].append(
            f"{gpu['vram_gb']} GB VRAM: generation may be slow or OOM. Prefer pipeline 512/1024 and low-VRAM."
        )
    if not disk["ok_for_trellis"]:
        report["warnings"].append(f"Only {disk['free_gb']} GB free; fresh TRELLIS needs ~25 GB.")
    if args.dry_run:
        report["dry_run"] = True
        report["plan"] = {
            "blender": blender,
            "gpu": gpu,
            "disk": disk,
            "harness": args.harness,
            "trellis": not args.without_trellis,
            "model_dir": args.model_dir,
            "trellis_python": args.trellis_python,
        }
        return report

    home = paths_module().data_home()
    home.mkdir(parents=True, exist_ok=True)

    host = "127.0.0.1"
    existing = load_config()
    port = int(args.mcp_port) if args.mcp_port else int(existing.get("mcp_port") or pick_port(host, 9876))
    token = "" if args.no_token else (existing.get("mcp_token") or secrets.token_hex(16))

    if not args.skip_mcp:
        try:
            mcp = install_mcp_venv(home)
            report["steps"].append({"step": "mcp", **mcp})
        except Exception as exc:  # noqa: BLE001
            report["errors"].append(f"MCP install failed: {exc}")
            return report
    else:
        mcp = {"executable": str(home / "venvs" / "mcp" / "bin" / "blender-skill-mcp")}

    if not args.skip_addon:
        addon = install_addon(blender, host, port, token)
        report["steps"].append({"step": "addon", **addon})
        if not addon.get("ok"):
            report["errors"].append("Blender add-on could not be enabled; use the panel to enable it manually.")
    else:
        addon = {"ok": True, "path": None}

    installed = install_skill(args.harness, project=args.project, force=args.force)
    report["steps"].append({"step": "skill", **installed})
    skill_root = Path(installed["installed"][0]) if installed.get("installed") else ROOT
    mcp_bin = Path(mcp["executable"])
    config_update: dict[str, Any] = {
        "skill_root": str(skill_root),
        "blender_bin": blender["path"],
        "mcp_executable": str(mcp_bin),
        "mcp_host": host,
        "mcp_port": port,
        "mcp_token": token,
        "trellis_vendor": str(skill_root / "trellis" / "vendor"),
        "trellis_bridge": str(skill_root / "trellis" / "bridge" / "trellis2_bridge.py"),
        "model_dir": str(args.model_dir or (home / "models" / TRELLIS_REPO.split("/")[-1])),
        "outputs_dir": str(home / "outputs"),
        "aux_dir": str(args.aux_dir or (Path(config_update["model_dir"]) / "aux")),
        "attn_backend": "flash_attn" if args.with_flash_attn else "xformers",
        "gpu_profile": gpu["profile"],
    }
    save_config(config_update)

    harness_report = configure_harnesses(args.harness, skill_root, mcp_bin, port, token, project=args.project)
    report["steps"].append({"step": "harness", **harness_report})

    if not args.without_trellis:
        trellis = setup_trellis(
            home,
            with_flash_attn=args.with_flash_attn,
            python_override=args.trellis_python,
            skip_build=args.skip_trellis_build,
            vendor_root=skill_root / "trellis" / "vendor",
        )
        report["steps"].append({"step": "trellis", **trellis})
        if trellis.get("ok"):
            config_update["trellis_python"] = trellis["python"]
            save_config({"trellis_python": trellis["python"]})
            if args.with_trellis_addon:
                addon_ui = install_trellis_addon(
                    blender,
                    vendor=Path(config_update["trellis_vendor"]),
                    python=Path(trellis["python"]),
                    model_dir=Path(config_update["model_dir"]),
                    output_dir=Path(config_update["outputs_dir"]),
                )
                report["steps"].append({"step": "trellis-addon", **addon_ui})
                if not addon_ui.get("ok"):
                    report["warnings"].append("TRELLIS.2 UI add-on could not be enabled; the MCP/CLI still work.")
            if not args.skip_weights:
                weights = download_all(Path(trellis["python"]), Path(config_update["model_dir"]),
                                       aux_dir=args.aux_dir)
                report["steps"].append({"step": "weights", **weights})
                if weights["aux"].get("gated"):
                    report["warnings"].append(
                        "Gated auxiliary models need license acceptance: "
                        + ", ".join(item["url"] for item in weights["aux"]["gated"])
                    )
                if not weights.get("ok"):
                    report["warnings"].append(
                        "TRELLIS auxiliary models are incomplete. Accept the gated licenses, set HF_TOKEN, "
                        "then run: python3 scripts/blender_skill.py trellis download"
                    )
        else:
            report["errors"].append("TRELLIS setup failed; see the trellis step output.")

    report["doctor"] = doctor()
    report["ok"] = not report["errors"] and report["doctor"]["ok"]
    return report


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #

def test_all(kind: str, args: argparse.Namespace) -> int:
    root = ROOT
    if kind in {"fast", "all"}:
        proc = run([sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"], timeout=600)
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        if proc.returncode != 0 and kind != "all":
            return proc.returncode
    if kind in {"mcp", "all"}:
        script = root / "tests" / "live_mcp.py"
        proc = run([sys.executable, str(script)], timeout=600)
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        if proc.returncode != 0:
            return proc.returncode
    if kind in {"trellis", "all"}:
        script = root / "tests" / "live_trellis.py"
        command = [sys.executable, str(script)]
        if getattr(args, "pipeline_type", None):
            command += ["--pipeline-type", args.pipeline_type]
        if getattr(args, "image", None):
            command += ["--image", args.image]
        proc = run(command, timeout=7200)
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        if proc.returncode != 0:
            return proc.returncode
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="blender-skill installer and doctor")
    parser.add_argument("--version", action="version", version="blender-skill 1.0.0")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="detect prerequisites and install everything")
    p_setup.add_argument("--harness", default="auto",
                         choices=["auto", "opencode", "claude", "codex", "cursor", "agents", "generic", "all"])
    p_setup.add_argument("--project", type=Path, default=None, help="install into a project skills directory")
    p_setup.add_argument("--without-trellis", action="store_true", help="skip the TRELLIS environment and weights")
    p_setup.add_argument("--skip-trellis-build", action="store_true", help="create the venv but skip package builds")
    p_setup.add_argument("--with-flash-attn", action="store_true", help="build flash-attn (slow)")
    p_setup.add_argument("--with-trellis-addon", action="store_true", help="install the optional TRELLIS.2 Blender UI add-on")
    p_setup.add_argument("--trellis-python", default=None, help="reuse an existing TRELLIS python")
    p_setup.add_argument("--model-dir", default=None, help="existing TRELLIS.2-4B weights directory")
    p_setup.add_argument("--aux-dir", type=Path, default=None, help="existing auxiliary model directory")
    p_setup.add_argument("--skip-mcp", action="store_true")
    p_setup.add_argument("--skip-addon", action="store_true")
    p_setup.add_argument("--skip-weights", action="store_true")
    p_setup.add_argument("--mcp-port", type=int, default=None)
    p_setup.add_argument("--no-token", action="store_true", help="disable the local MCP token")
    p_setup.add_argument("--force", action="store_true", help="replace an existing installed skill without backup")
    p_setup.add_argument("--dry-run", action="store_true")
    p_setup.set_defaults(func=lambda a: _print(setup(a)))

    p_install = sub.add_parser("install", help="install only the skill payload and harness config")
    p_install.add_argument("--harness", default="auto",
                           choices=["auto", "opencode", "claude", "codex", "cursor", "agents", "generic", "all"])
    p_install.add_argument("--project", type=Path, default=None)
    p_install.add_argument("--force", action="store_true")
    p_install.set_defaults(func=lambda a: _print(_install_only(a)))

    p_doctor = sub.add_parser("doctor", help="report prerequisite and install state")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.set_defaults(func=lambda a: _print(doctor()))

    p_trellis = sub.add_parser("trellis", help="run TRELLIS.2 commands")
    tsub = p_trellis.add_subparsers(dest="trellis_command", required=True)
    tsub.add_parser("doctor")
    p_gen = tsub.add_parser("generate")
    p_gen.add_argument("--image", required=True)
    p_gen.add_argument("--output", required=True)
    p_gen.add_argument("--pipeline-type", default="1024_cascade")
    p_gen.add_argument("--seed", type=int, default=42)
    p_gen.add_argument("--num-samples", type=int, default=1)
    p_gen.add_argument("--decimation-target", type=int, default=250000)
    p_gen.add_argument("--texture-size", type=int, default=2048)
    p_gen.add_argument("--alpha-mode", default="opaque")
    p_gen.add_argument("--low-vram", action="store_true")
    p_gen.add_argument("--no-remesh", action="store_true")
    p_tex = tsub.add_parser("texture")
    p_tex.add_argument("--mesh", required=True)
    p_tex.add_argument("--image", required=True)
    p_tex.add_argument("--output", required=True)
    p_tex.add_argument("--resolution", type=int, default=1024)
    p_tex.add_argument("--texture-size", type=int, default=2048)
    p_tex.add_argument("--seed", type=int, default=42)
    p_tex.add_argument("--low-vram", action="store_true")
    p_dl = tsub.add_parser("download")
    p_dl.add_argument("--resume", action="store_true")
    p_dl.add_argument("--aux-dir", type=Path, default=None)

    def trellis_dispatch(a: argparse.Namespace) -> int:
        if a.trellis_command == "doctor":
            return run_trellis(["doctor"])
        if a.trellis_command == "generate":
            args = ["generate", "--image", a.image, "--output", a.output,
                    "--pipeline-type", a.pipeline_type, "--seed", str(a.seed),
                    "--num-samples", str(a.num_samples), "--decimation-target", str(a.decimation_target),
                    "--texture-size", str(a.texture_size), "--alpha-mode", a.alpha_mode]
            args.append("--no-remesh" if a.no_remesh else "--remesh")
            if a.low_vram:
                args.append("--low-vram")
            return run_trellis(args)
        if a.trellis_command == "texture":
            args = ["texture", "--mesh", a.mesh, "--image", a.image, "--output", a.output,
                    "--resolution", str(a.resolution), "--texture-size", str(a.texture_size),
                    "--seed", str(a.seed)]
            if a.low_vram:
                args.append("--low-vram")
            return run_trellis(args)
        if a.trellis_command == "download":
            config = load_config()
            python = config.get("trellis_python")
            if not python:
                raise SystemExit("TRELLIS python missing; run setup first")
            result = download_all(Path(python), Path(config.get("model_dir")), aux_dir=getattr(a, "aux_dir", None))
            print(json.dumps(result, indent=2))
            return 0 if result.get("ok") else 1
        return 2

    p_trellis.set_defaults(func=trellis_dispatch)

    p_test = sub.add_parser("test", help="run packaging, MCP, and TRELLIS tests")
    p_test.add_argument("kind", choices=["fast", "mcp", "trellis", "all"])
    p_test.add_argument("--pipeline-type", default="512")
    p_test.add_argument("--image", default=None)
    p_test.set_defaults(func=lambda a: test_all(a.kind, a))

    p_status = sub.add_parser("status", help="show resolved paths and versions")
    p_status.set_defaults(func=lambda a: _print(doctor()))

    return parser


def _install_only(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config()
    port = int(config.get("mcp_port") or 9876)
    token = str(config.get("mcp_token") or "")
    mcp_bin = Path(config.get("mcp_executable") or (paths_module().data_home() / "venvs" / "mcp" / "bin" / "blender-skill-mcp"))
    installed = install_skill(args.harness, project=args.project, force=args.force)
    skill_root = Path(installed["installed"][0]) if installed.get("installed") else ROOT
    config["skill_root"] = str(skill_root)
    save_config({"skill_root": str(skill_root)})
    harness = configure_harnesses(args.harness, skill_root, mcp_bin, port, token, project=args.project)
    return {"skill": installed, "harness": harness}


def _print(data: Any) -> int:
    print(json.dumps(data, indent=2, default=str))
    if isinstance(data, dict) and data.get("ok") is False:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
