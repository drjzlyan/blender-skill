"""MCP tool implementations for Blender, TRELLIS.2, and the bundled corpus."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from . import paths, snippets
from .bridge import BlenderBridge, BridgeError

try:
    from mcp.server.fastmcp import Image
except Exception:  # pragma: no cover - older/newer SDKs
    Image = None  # type: ignore


def _bridge() -> BlenderBridge:
    return BlenderBridge()


def _exec(code: str, timeout: float = 60.0) -> dict[str, Any]:
    return _bridge().execute(code, timeout=timeout)


def _image_from(result: dict[str, Any]) -> Any:
    data = base64.b64decode(result.get("base64", ""))
    if Image is None:
        return {"format": "png", "bytes": len(data), "base64": result.get("base64")}
    try:
        return Image(data=data, format="png")
    except TypeError:
        return Image(data=data)


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9_]+", text.lower()) if t and len(t) > 1]


def register_tools(mcp: Any) -> None:
    @mcp.tool()
    def execute_blender_code(code: str, strict_json: bool = True, timeout_sec: float = 60.0) -> dict[str, Any]:
        """Execute Python in the running Blender and return result/stdout/stderr.

        Assign a JSON-serialisable value to a variable named ``result`` to return
        data. The code runs on Blender's main thread, so keep it bounded; long
        jobs should use timers or the TRELLIS tools.
        """
        try:
            bridge = _bridge()
            return bridge.execute(code, strict_json=strict_json, timeout=float(timeout_sec))
        except BridgeError as exc:
            return {"ok": False, "error": str(exc)}

    @mcp.tool()
    def get_objects_summary() -> dict[str, Any]:
        """Return the scene collection hierarchy, objects, selection, and orphans."""
        try:
            return _exec(snippets.OBJECTS_SUMMARY)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_object_detail_summary(name: str) -> dict[str, Any]:
        """Return transforms, modifiers, constraints, materials, visibility, and children for one object."""
        try:
            return _exec(snippets.OBJECT_DETAIL.format(name=json.dumps(name)))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_blendfile_summary_datablocks() -> dict[str, Any]:
        """Return data-block counts, active workspace, scene, and render engine."""
        try:
            return _exec(snippets.DATABLOCKS)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_blendfile_summary_path_info() -> dict[str, Any]:
        """Return the blend file path, save state, size, modified time, and backups."""
        try:
            return _exec(snippets.PATH_INFO)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_blendfile_summary_missing_files() -> dict[str, Any]:
        """Report external files referenced by the blend that do not exist on disk."""
        try:
            return _exec(snippets.MISSING_FILES)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_blendfile_summary_of_linked_libraries() -> dict[str, Any]:
        """Return directly linked libraries with resolved paths and existence state."""
        try:
            return _exec(snippets.LINKED_LIBRARIES)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_blendfile_summary_usage_guess() -> dict[str, Any]:
        """Guess the scene's likely use (archviz, game asset, character, VFX, ...) with evidence."""
        try:
            return _exec(snippets.USAGE_GUESS)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_screenshot_of_window_as_image() -> Any:
        """Capture the whole Blender window as a PNG image."""
        try:
            return _image_from(_exec(snippets.screenshot_code(None), timeout=30)["result"])
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_screenshot_of_area_as_image(area_ui_type: str) -> Any:
        """Capture one editor area (VIEW_3D, UV, ShaderNodeTree, ...) as a PNG image."""
        try:
            return _image_from(_exec(snippets.screenshot_code(area_ui_type), timeout=30)["result"])
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_screenshot_of_window_as_json() -> dict[str, Any]:
        """Describe window layout, areas, workspaces, active object, selection, and mode."""
        try:
            return _exec(snippets.WINDOW_JSON)["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def jump_to_tab_by_name(name: str) -> dict[str, Any]:
        """Switch the active workspace to a named workspace."""
        try:
            return _exec(snippets.jump_workspace_name(name))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def jump_to_tab_by_space_type(space_type: str) -> dict[str, Any]:
        """Switch to the first workspace containing an area of the requested type."""
        try:
            return _exec(snippets.jump_workspace_space(space_type))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def jump_to_view3d_object_by_name(name: str) -> dict[str, Any]:
        """Select, activate, and frame an object in the 3D viewport."""
        try:
            return _exec(snippets.jump_object(name, False))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def jump_to_view3d_object_data_by_name(name: str) -> dict[str, Any]:
        """Select and frame the object whose data-block has this name."""
        try:
            return _exec(snippets.jump_object(name, True))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def render_viewport_to_path(
        path: str,
        width: int | None = None,
        height: int | None = None,
        timeout_sec: float = 900.0,
    ) -> dict[str, Any]:
        """Render the scene with current settings to an explicit PNG path."""
        try:
            return _exec(snippets.render_code(path, False, width, height), timeout=float(timeout_sec))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def render_thumbnail_to_path(path: str, timeout_sec: float = 300.0) -> dict[str, Any]:
        """Render a fast 25%-resolution low-sample thumbnail to a PNG path."""
        try:
            return _exec(snippets.render_code(path, True, None, None), timeout=float(timeout_sec))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_python_api_docs(identifier: str) -> dict[str, Any]:
        """Return the docstring and signature for a bpy/bmesh/mathutils identifier from the running Blender."""
        try:
            return _exec(snippets.api_doc_code(identifier))["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def search_api_docs(query: str, max_results: int = 20, refresh: bool = False) -> dict[str, Any]:
        """Full-text search over docstrings of the running Blender's Python API."""
        try:
            return _search_api(query, max_results, refresh)
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def search_manual_docs(query: str, max_results: int = 20) -> dict[str, Any]:
        """Search the bundled Blender workflow corpus and any downloaded manual cache."""
        return _search_manual(query, max_results)

    @mcp.tool()
    def trellis2_doctor() -> dict[str, Any]:
        """Check the local TRELLIS.2 venv, CUDA extensions, and model weights."""
        return _run_trellis(["doctor"], timeout=300)

    @mcp.tool()
    def trellis2_generate(
        image: str,
        output: str,
        pipeline_type: str = "1024_cascade",
        seed: int = 42,
        num_samples: int = 1,
        decimation_target: int = 250000,
        texture_size: int = 2048,
        remesh: bool = True,
        alpha_mode: str = "opaque",
        low_vram: bool | None = None,
        timeout_sec: float = 3600.0,
    ) -> dict[str, Any]:
        """Generate a PBR GLB from a reference image with local TRELLIS.2."""
        args = [
            "generate",
            "--image", os.path.abspath(os.path.expanduser(image)),
            "--output", os.path.abspath(os.path.expanduser(output)),
            "--pipeline-type", pipeline_type,
            "--seed", str(int(seed)),
            "--num-samples", str(int(num_samples)),
            "--decimation-target", str(int(decimation_target)),
            "--texture-size", str(int(texture_size)),
            "--alpha-mode", alpha_mode,
        ]
        args.append("--remesh" if remesh else "--no-remesh")
        if low_vram is True:
            args.append("--low-vram")
        elif low_vram is False:
            args.append("--no-low-vram")
        return _run_trellis(args, timeout=float(timeout_sec))

    @mcp.tool()
    def trellis2_texture(
        mesh: str,
        image: str,
        output: str,
        resolution: int = 1024,
        texture_size: int = 2048,
        seed: int = 42,
        low_vram: bool | None = None,
        timeout_sec: float = 3600.0,
    ) -> dict[str, Any]:
        """PBR-texture an existing mesh with local TRELLIS.2."""
        args = [
            "texture",
            "--mesh", os.path.abspath(os.path.expanduser(mesh)),
            "--image", os.path.abspath(os.path.expanduser(image)),
            "--output", os.path.abspath(os.path.expanduser(output)),
            "--resolution", str(int(resolution)),
            "--texture-size", str(int(texture_size)),
            "--seed", str(int(seed)),
        ]
        if low_vram is True:
            args.append("--low-vram")
        elif low_vram is False:
            args.append("--no-low-vram")
        return _run_trellis(args, timeout=float(timeout_sec))

    @mcp.tool()
    def trellis2_import(
        glb: str,
        collection: str = "COL_TRELLIS2",
        name_prefix: str = "GEN_Trellis2",
        apply_alpha: bool = True,
    ) -> dict[str, Any]:
        """Import a generated GLB into a provenance-tagged collection in Blender."""
        try:
            return _exec(
                snippets.import_code(glb, collection, name_prefix, apply_alpha),
                timeout=300,
            )["result"]
        except BridgeError as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def blender_skill_status() -> dict[str, Any]:
        """Report skill paths, Blender connection, add-on state, GPU profile, and TRELLIS readiness."""
        config = paths.load_config()
        status: dict[str, Any] = {
            "skill_root": str(paths.skill_root()),
            "data_home": str(paths.data_home()),
            "config": str(paths.config_home()),
            "mcp": {"host": paths.mcp_host(), "port": paths.mcp_port(), "token_required": bool(paths.mcp_token())},
            "config_values": {k: v for k, v in config.items() if "token" not in k},
            "blender": None,
            "trellis": {
                "python": str(paths.trellis_python()) if paths.trellis_python() else None,
                "vendor": str(paths.trellis_vendor()),
                "bridge": str(paths.bridge_script()),
                "model_dir": str(paths.model_dir()),
                "model_present": (paths.model_dir() / "pipeline.json").is_file(),
            },
        }
        try:
            status["blender"] = _bridge().state()
        except BridgeError as exc:
            status["blender"] = {"connected": False, "error": str(exc)}
        status["gpu"] = _gpu_info()
        return status


def _search_api(query: str, max_results: int, refresh: bool) -> dict[str, Any]:
    if not query.strip():
        return {"error": "empty query"}
    state = _bridge().state()
    version = str(state.get("blender", "unknown")).replace(" ", "_")
    cache = paths.cache_home() / f"api_index_{version}.json"
    entries: list[dict[str, Any]]
    if cache.is_file() and not refresh:
        try:
            entries = json.loads(cache.read_text(encoding="utf-8")).get("entries", [])
        except Exception:
            entries = []
    else:
        entries = []
    if not entries:
        payload = _exec(snippets.API_INDEX, timeout=600)["result"]
        entries = payload.get("entries", []) if isinstance(payload, dict) else []
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"version": version, "entries": entries}), encoding="utf-8")
    tokens = _tokens(query)
    if not tokens:
        return {"error": "query has no searchable tokens"}
    ranked: list[tuple[float, dict[str, Any]]] = []
    for entry in entries:
        haystack = (entry.get("id", "") + " " + entry.get("doc", "")).lower()
        if not all(token in haystack for token in tokens):
            continue
        ident = entry.get("id", "").lower()
        score = sum(3.0 for token in tokens if token in ident) + sum(0.2 for token in tokens if token in haystack)
        ranked.append((score, entry))
    ranked.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    results = []
    for score, entry in ranked[: max(1, min(int(max_results), 100))]:
        doc = entry.get("doc", "")
        results.append(
            {
                "identifier": entry.get("id"),
                "kind": entry.get("kind"),
                "score": round(score, 2),
                "doc": doc if len(doc) <= 1500 else doc[:1500] + "...",
            }
        )
    return {"query": query, "version": version, "total_entries": len(entries), "results": results}


def _search_manual(query: str, max_results: int) -> dict[str, Any]:
    if not query.strip():
        return {"error": "empty query"}
    tokens = _tokens(query)
    if not tokens:
        return {"error": "query has no searchable tokens"}
    roots = [paths.skill_root() / "references"]
    docs_cache = paths.cache_home() / "docs"
    if docs_cache.is_dir():
        roots.append(docs_cache)
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for pattern in ("*.md", "*.rst"):
            files.extend(root.rglob(pattern))
    scored: list[tuple[float, str, str]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        paragraphs = re.split(r"\n\s*\n", text)
        for paragraph in paragraphs:
            low = paragraph.lower()
            if not all(token in low for token in tokens):
                continue
            score = sum(low.count(token) for token in tokens)
            if score == 0:
                continue
            snippet = re.sub(r"\s+", " ", paragraph).strip()
            scored.append((float(score), str(path), snippet[:500]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    results = [
        {"path": _display_path(Path(path)), "score": round(score, 2), "snippet": snippet}
        for score, path, snippet in scored[: max(1, min(int(max_results), 100))]
    ]
    return {"query": query, "searched_files": len(files), "results": results}


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(paths.skill_root()))
    except ValueError:
        return str(path)


def _run_trellis(args: list[str], timeout: float) -> dict[str, Any]:
    python = paths.trellis_python()
    if python is None or not Path(python).is_file():
        return {
            "ok": False,
            "error": "TRELLIS Python environment not found",
            "hint": "Run: python3 scripts/blender_skill.py setup --with-trellis",
            "expected": str(paths.data_home() / "venvs" / "trellis" / "bin" / "python"),
        }
    bridge = paths.bridge_script()
    if not bridge.is_file():
        return {"ok": False, "error": f"TRELLIS bridge not found: {bridge}"}
    vendor = paths.trellis_vendor()
    model = paths.model_dir()
    config = paths.load_config()
    command = [
        str(python),
        str(bridge),
        "--vendor-dir", str(vendor),
        "--model", str(model),
        *args,
    ]
    env = os.environ.copy()
    env.setdefault("ATTN_BACKEND", str(config.get("attn_backend") or "sdpa"))
    env["TRELLIS2_VENDOR"] = str(vendor)
    env["TRELLIS2_MODEL"] = str(model)
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(paths.skill_root()),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"TRELLIS job timed out after {timeout}s", "command": command}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "command": command}
    payload: dict[str, Any] = {}
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("TRELLIS2_RESULT "):
            try:
                payload = json.loads(line[len("TRELLIS2_RESULT ") :])
            except Exception:
                payload = {}
            break
    if not payload:
        payload = {
            "ok": False,
            "error": "no TRELLIS2_RESULT line",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    payload.setdefault("returncode", proc.returncode)
    if proc.returncode != 0:
        payload.setdefault("stderr_tail", proc.stderr[-4000:])
    return payload


def _gpu_info() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            name, memory, driver = [part.strip() for part in proc.stdout.splitlines()[0].split(",")]
            vram = round(float(memory) / 1024, 1)
            if vram >= 48:
                profile = "high"
            elif vram >= 24:
                profile = "recommended"
            elif vram >= 16:
                profile = "medium"
            elif vram >= 8:
                profile = "low"
            else:
                profile = "minimal"
            return {"vendor": "nvidia", "name": name, "vram_gb": vram, "driver": driver, "profile": profile}
    except Exception:
        pass
    return {"vendor": None, "profile": "mcp_only", "note": "No NVIDIA GPU detected; TRELLIS.2 unavailable"}
