from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import bpy
from mathutils import Matrix, Vector

from .preferences import get_preferences


@dataclass
class Job:
    process: subprocess.Popen
    log_path: Path
    output_path: Path
    task: str
    keep_logs: bool
    fit_bounds: Optional[tuple] = None
    original_names: List[str] = field(default_factory=list)
    temp_paths: List[Path] = field(default_factory=list)
    started: float = field(default_factory=time.time)
    log_handle: Any = None
    last_line_count: int = 0


_ACTIVE_JOB: Optional[Job] = None
_LAST_LOG: Optional[Path] = None
_PROGRESS_RE = re.compile(r"TRELLIS2_PROGRESS\s+(\d+)\s+(.*)")


def is_running() -> bool:
    return _ACTIVE_JOB is not None


def last_log_path() -> Optional[Path]:
    return _LAST_LOG


def _sanitize(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")
    return cleaned or "asset"


def _ensure_collection(scene) -> bpy.types.Collection:
    name = "COL_TRELLIS2"
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
    return collection


def _tail(path: Path, max_bytes: int = 16384) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - max_bytes))
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _read_result(log_path: Path, output_path: Path) -> Optional[Dict[str, Any]]:
    sidecar = output_path.with_suffix(output_path.suffix + ".json")
    if sidecar.is_file():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    text = _tail(log_path, 65536)
    for line in reversed(text.splitlines()):
        if line.startswith("TRELLIS2_RESULT "):
            try:
                return json.loads(line[len("TRELLIS2_RESULT ") :])
            except json.JSONDecodeError:
                continue
    return None


def _world_bounds(objects: List[bpy.types.Object]):
    points: List[Vector] = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return None
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def selection_bounds(context) -> Optional[tuple]:
    selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
    if not selected:
        return None
    bpy.context.view_layer.update()
    return _world_bounds(selected)


def _fit_to_bounds(objects: List[bpy.types.Object], target_bounds) -> None:
    current = _world_bounds(objects)
    if current is None or target_bounds is None:
        return
    cur_min, cur_max = current
    tgt_min, tgt_max = target_bounds
    cur_size = cur_max - cur_min
    tgt_size = tgt_max - tgt_min
    factors = [tgt_size[i] / cur_size[i] for i in range(3) if cur_size[i] > 1e-9]
    if not factors:
        return
    factor = max(factors)
    cur_center = (cur_min + cur_max) * 0.5
    tgt_center = (tgt_min + tgt_max) * 0.5
    matrix = Matrix.Translation(tgt_center) @ Matrix.Scale(factor, 4) @ Matrix.Translation(-cur_center)
    roots = [obj for obj in objects if obj.parent not in objects]
    for obj in roots:
        obj.matrix_world = matrix @ obj.matrix_world
    bpy.context.view_layer.update()


def _enable_alpha(material: bpy.types.Material) -> bool:
    if material is None or not material.use_nodes or material.node_tree is None:
        return False
    nodes = material.node_tree.nodes
    bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return False
    alpha_input = bsdf.inputs.get("Alpha")
    base_input = bsdf.inputs.get("Base Color")
    if alpha_input is None or base_input is None or not base_input.links:
        return False
    source = base_input.links[0].from_node
    if source.type != "TEX_IMAGE" or source.image is None:
        return False
    if not alpha_input.links:
        material.node_tree.links.new(source.outputs["Alpha"], alpha_input)
    if hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "DITHERED"
        except TypeError:
            pass
    if hasattr(material, "blend_method"):
        try:
            material.blend_method = "BLEND"
        except TypeError:
            pass
    if hasattr(material, "show_transparent_back"):
        material.show_transparent_back = False
    return True


def _import_glb(
    context,
    paths: List[str],
    prefix: str,
    import_scale: float,
    apply_alpha: bool,
    fit_bounds=None,
) -> List[bpy.types.Object]:
    scene = context.scene
    collection = _ensure_collection(scene)
    before = set(bpy.data.objects)
    imported_all: List[bpy.types.Object] = []

    for path in paths:
        result = bpy.ops.import_scene.gltf(filepath=path)
        if "FINISHED" not in result:
            continue
        new_objects = [obj for obj in bpy.data.objects if obj not in before]
        before.update(new_objects)
        imported_all.extend(new_objects)

        for index, obj in enumerate(new_objects):
            if obj.name not in collection.objects:
                try:
                    collection.objects.link(obj)
                except RuntimeError:
                    pass
            for other in list(obj.users_collection):
                if other != collection:
                    other.objects.unlink(obj)

            base = _sanitize(Path(path).stem)
            obj.name = f"{prefix}_{base}_{index:02d}"
            if obj.data is not None:
                obj.data.name = obj.name
            obj["trellis2_source"] = path
            obj["trellis2_generated_at"] = datetime.now().isoformat(timespec="seconds")
            if apply_alpha:
                for slot in obj.material_slots:
                    _enable_alpha(slot.material)

    if fit_bounds is not None:
        _fit_to_bounds(imported_all, fit_bounds)

    if import_scale and abs(import_scale - 1.0) > 1e-9:
        roots = [obj for obj in imported_all if obj.parent not in imported_all]
        for obj in roots:
            obj.scale = tuple(component * import_scale for component in obj.scale)

    bpy.context.view_layer.update()
    if imported_all:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in imported_all:
            obj.select_set(True)
        context.view_layer.objects.active = imported_all[0]
    return imported_all


def _finish(job: Job, context) -> None:
    global _ACTIVE_JOB, _LAST_LOG
    scene = context.scene
    return_code = job.process.poll()

    try:
        job.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    if job.log_handle is not None:
        try:
            job.log_handle.close()
        except OSError:
            pass

    result = _read_result(job.log_path, job.output_path)
    success = return_code == 0 and result is not None and result.get("ok")

    if success:
        paths = [item["path"] for item in result.get("outputs", []) if Path(item["path"]).is_file()]
        prefs = get_preferences(context)
        imported = _import_glb(
            context,
            paths,
            prefix=scene.trellis2_name_prefix,
            import_scale=scene.trellis2_import_scale,
            apply_alpha=scene.trellis2_apply_alpha,
            fit_bounds=job.fit_bounds if scene.trellis2_fit_to_original else None,
        )
        scene.trellis2_last_output = paths[0] if paths else ""
        elapsed = round(time.time() - job.started, 1)
        scene.trellis2_status = f"Done in {elapsed}s - imported {len(imported)} object(s)"
        scene.trellis2_progress = 1.0
    else:
        message = "Unknown error"
        if result and result.get("error"):
            message = result["error"]
        elif return_code not in (None, 0):
            message = f"Process exited with code {return_code}"
        tail = _tail(job.log_path, 4096).strip().splitlines()
        if tail and message == "Unknown error":
            message = tail[-1]
        scene.trellis2_status = f"Failed: {message[:220]}"
        scene.trellis2_progress = 1.0

    for temp in job.temp_paths:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass

    _LAST_LOG = job.log_path
    if not job.keep_logs and job.log_path.is_file():
        try:
            job.log_path.unlink()
        except OSError:
            pass

    scene.trellis2_running = False
    _ACTIVE_JOB = None
    try:
        context.window_manager.progress_end()
    except (AttributeError, RuntimeError):
        pass


def _tick():
    global _ACTIVE_JOB
    job = _ACTIVE_JOB
    if job is None:
        return None

    context = bpy.context
    scene = context.scene
    text = _tail(job.log_path)
    lines = text.splitlines()
    if lines:
        for line in reversed(lines):
            match = _PROGRESS_RE.match(line.strip())
            if match:
                percent = int(match.group(1))
                message = match.group(2).strip()
                scene.trellis2_progress = percent / 100.0
                scene.trellis2_status = message
                try:
                    context.window_manager.progress_update(percent)
                except (AttributeError, RuntimeError):
                    pass
                break

    if job.process.poll() is None:
        return 0.5

    try:
        _finish(job, context)
    except Exception as exc:  # noqa: BLE001
        scene.trellis2_status = f"Import failed: {exc}"
        scene.trellis2_running = False
        _ACTIVE_JOB = None
        try:
            context.window_manager.progress_end()
        except (AttributeError, RuntimeError):
            pass
    return None


def _build_env(context, repo: Path, prefs) -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    env["ATTN_BACKEND"] = prefs.attn_backend
    env["TRELLIS2_VENDOR"] = str(repo)
    if prefs.hf_home:
        env["HF_HOME"] = bpy.path.abspath(prefs.hf_home)
    return env


def _job_paths(context, prefs, kind: str):
    output_dir = context.scene.trellis2_output_dir or prefs.output_dir
    if not output_dir:
        home = os.environ.get("BLENDER_SKILL_HOME")
        output_dir = str(Path(home) / "outputs") if home else str(Path.home() / "blender-skill-outputs")
    output_dir = Path(bpy.path.abspath(output_dir)).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"trellis2_{kind}_{stamp}.glb"
    log_path = output_dir / f"trellis2_{kind}_{stamp}.log"
    return output_path, log_path


def _launch(context, cmd: List[str], env: Dict[str, str], repo: Path, output_path: Path, log_path: Path, task: str, keep_logs: bool, fit_bounds=None, temp_paths=None):
    global _ACTIVE_JOB, _LAST_LOG
    if _ACTIVE_JOB is not None:
        raise RuntimeError("A TRELLIS.2 job is already running")

    log_handle = log_path.open("wb")
    process = subprocess.Popen(
        cmd,
        cwd=str(repo),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    job = Job(
        process=process,
        log_path=log_path,
        output_path=output_path,
        task=task,
        keep_logs=keep_logs,
        fit_bounds=fit_bounds,
        log_handle=log_handle,
        temp_paths=list(temp_paths or []),
    )
    _ACTIVE_JOB = job
    _LAST_LOG = log_path
    context.scene.trellis2_running = True
    context.scene.trellis2_progress = 0.0
    context.scene.trellis2_status = "Starting..."
    try:
        context.window_manager.progress_begin(0, 100)
    except (AttributeError, RuntimeError):
        pass
    bpy.app.timers.register(_tick, first_interval=0.5, persistent=True)
    return job


def _validate(context, prefs) -> Path:
    repo = prefs.resolved_repo()
    bridge = prefs.resolved_bridge()
    if not bridge.is_file():
        raise FileNotFoundError(f"Bridge script not found: {bridge}")
    python = Path(prefs.resolved_python())
    if not python.is_file():
        raise FileNotFoundError(f"Python executable not found: {python}")
    return repo


def start_generate(context) -> Job:
    prefs = get_preferences(context)
    repo = _validate(context, prefs)
    scene = context.scene
    image = Path(bpy.path.abspath(scene.trellis2_image_path)).expanduser()
    if not image.is_file():
        raise FileNotFoundError(f"Image not found: {image}")

    output_path, log_path = _job_paths(context, prefs, "image3d")
    cmd = [
        prefs.resolved_python(),
        str(prefs.resolved_bridge()),
        "--vendor-dir",
        str(repo),
        "--model",
        prefs.model,
        "generate",
        "--image",
        str(image),
        "--output",
        str(output_path),
        "--seed",
        str(scene.trellis2_seed),
        "--num-samples",
        str(scene.trellis2_num_samples),
        "--pipeline-type",
        scene.trellis2_pipeline_type,
        "--decimation-target",
        str(scene.trellis2_decimation),
        "--texture-size",
        scene.trellis2_texture_size,
        "--alpha-mode",
        "blend" if scene.trellis2_apply_alpha else "opaque",
    ]
    cmd.append("--no-remesh" if not scene.trellis2_remesh else "--remesh")
    env = _build_env(context, repo, prefs)
    return _launch(
        context,
        cmd,
        env,
        repo,
        output_path,
        log_path,
        "image3d",
        prefs.keep_logs,
    )


def start_texture(context) -> Job:
    prefs = get_preferences(context)
    repo = _validate(context, prefs)
    scene = context.scene
    image = Path(bpy.path.abspath(scene.trellis2_texture_image_path)).expanduser()
    if not image.is_file():
        raise FileNotFoundError(f"Reference image not found: {image}")
    selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
    if not selected:
        raise RuntimeError("Select at least one mesh object to texture")

    fit_bounds = selection_bounds(context) if scene.trellis2_fit_to_original else None
    output_path, log_path = _job_paths(context, prefs, "textured")
    temp_mesh = log_path.with_suffix(".input.glb")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected:
        obj.select_set(True)
    context.view_layer.objects.active = selected[0]
    export_result = bpy.ops.export_scene.gltf(
        filepath=str(temp_mesh),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    if "FINISHED" not in export_result:
        raise RuntimeError("Failed to export the selected mesh to a temporary GLB")

    cmd = [
        prefs.resolved_python(),
        str(prefs.resolved_bridge()),
        "--vendor-dir",
        str(repo),
        "--model",
        prefs.model,
        "texture",
        "--mesh",
        str(temp_mesh),
        "--image",
        str(image),
        "--output",
        str(output_path),
        "--seed",
        str(scene.trellis2_seed),
        "--texture-size",
        scene.trellis2_texture_size,
    ]
    env = _build_env(context, repo, prefs)
    return _launch(
        context,
        cmd,
        env,
        repo,
        output_path,
        log_path,
        "textured",
        prefs.keep_logs,
        fit_bounds=fit_bounds,
        temp_paths=[temp_mesh],
    )


def cancel(context) -> bool:
    global _ACTIVE_JOB
    job = _ACTIVE_JOB
    if job is None:
        return False
    try:
        os.killpg(os.getpgid(job.process.pid), signal.SIGTERM)
    except OSError:
        try:
            job.process.terminate()
        except OSError:
            pass
    try:
        job.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(job.process.pid), signal.SIGKILL)
        except OSError:
            pass
    if job.log_handle is not None:
        try:
            job.log_handle.close()
        except OSError:
            pass
    context.scene.trellis2_status = "Cancelled"
    context.scene.trellis2_running = False
    context.scene.trellis2_progress = 0.0
    _ACTIVE_JOB = None
    try:
        context.window_manager.progress_end()
    except (AttributeError, RuntimeError):
        pass
    return True


def run_doctor(context) -> Dict[str, Any]:
    prefs = get_preferences(context)
    repo = prefs.resolved_repo()
    bridge = prefs.resolved_bridge()
    python = Path(prefs.resolved_python())
    if not bridge.is_file():
        raise FileNotFoundError(f"Bridge script not found: {bridge}")
    if not python.is_file():
        raise FileNotFoundError(f"Python executable not found: {python}")
    env = _build_env(context, repo, prefs)
    completed = subprocess.run(
        [str(python), str(bridge), "--vendor-dir", str(repo), "--model", prefs.model, "doctor"],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result: Dict[str, Any] = {}
    for line in completed.stdout.splitlines():
        if line.startswith("TRELLIS2_RESULT "):
            result = json.loads(line[len("TRELLIS2_RESULT ") :])
            break
    if not result:
        result = {
            "ok": False,
            "error": completed.stderr.strip() or "No doctor result returned",
        }
    return result


def import_last(context, path: str) -> List[bpy.types.Object]:
    prefs = get_preferences(context)
    return _import_glb(
        context,
        [path],
        prefix=context.scene.trellis2_name_prefix,
        import_scale=context.scene.trellis2_import_scale,
        apply_alpha=context.scene.trellis2_apply_alpha,
    )
