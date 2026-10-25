#!/usr/bin/env python3
"""TRELLIS.2 -> Blender bridge.

Runs TRELLIS.2 inference in its own Python environment and writes GLB files
plus a JSON sidecar that the Blender add-on (or an agent) can consume.

Examples
--------
    python trellis2_bridge.py doctor
    python trellis2_bridge.py generate --image input.png --output out/asset.glb
    python trellis2_bridge.py texture --mesh input.glb --image ref.png --output out/textured.glb

Progress is emitted as ``TRELLIS2_PROGRESS <percent> <message>`` lines so the
Blender add-on can show a progress bar without importing torch in Blender.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

# Some networks stall on IPv6 connections to the Hugging Face CDN. Force IPv4
# by default; set TRELLIS2_FORCE_IPV4=0 to opt out.
if os.environ.get("TRELLIS2_FORCE_IPV4", "1") == "1":
    import socket

    _original_getaddrinfo = socket.getaddrinfo

    def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = _ipv4_only

DEFAULT_MODEL = os.environ.get("TRELLIS2_MODEL", "microsoft/TRELLIS.2-4B")
DEFAULT_AABB = [[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]]


def _bootstrap_vendor(vendor: str) -> None:
    """Put the vendored inference code ahead of any system install."""
    path = str(Path(vendor).expanduser().resolve())
    if path not in sys.path:
        sys.path.insert(0, path)


def _progress(percent: int, message: str) -> None:
    print(f"TRELLIS2_PROGRESS {max(0, min(100, int(percent)))} {message}", flush=True)


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%dT%H%M%S")


def _resolve_outputs(output: str, stem_hint: str, index: int, count: int, suffix: str = ".glb") -> Path:
    out = Path(output).expanduser().resolve()
    if out.suffix.lower() == ".glb":
        if count > 1:
            return out.with_name(f"{out.stem}_{index:02d}{out.suffix}")
        return out
    out.mkdir(parents=True, exist_ok=True)
    base = f"{stem_hint}_{_now_stamp()}"
    if count > 1:
        base = f"{base}_{index:02d}"
    return out / f"{base}{suffix}"


def _write_sidecar(path: Path, metadata: Dict[str, Any]) -> None:
    sidecar = path.with_suffix(path.suffix + ".json")
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _emit_result(metadata: Dict[str, Any]) -> None:
    print("TRELLIS2_RESULT " + json.dumps(metadata, default=str), flush=True)


def _cuda_info() -> Dict[str, Any]:
    import torch

    info: Dict[str, Any] = {
        "torch": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": torch.version.cuda,
    }
    if torch.cuda.is_available():
        info["device"] = torch.cuda.get_device_name(0)
        info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
    return info


def _check_module(name: str) -> Dict[str, Any]:
    import importlib.util

    spec = importlib.util.find_spec(name)
    return {"installed": spec is not None, "origin": getattr(spec, "origin", None) if spec else None}


def cmd_doctor(args: argparse.Namespace) -> int:
    vendor = Path(args.vendor_dir).expanduser().resolve()
    report: Dict[str, Any] = {
        "ok": True,
        "task": "doctor",
        "vendor_dir": str(vendor),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "model": args.model,
        "checks": {},
        "warnings": [],
        "errors": [],
    }

    if not (vendor / "trellis2").is_dir():
        report["ok"] = False
        report["errors"].append(f"trellis2 package not found under {vendor}")
    if not (vendor / "o-voxel").is_dir():
        report["ok"] = False
        report["errors"].append(f"o-voxel package not found under {vendor}")

    try:
        report["checks"]["cuda"] = _cuda_info()
        if not report["checks"]["cuda"].get("cuda_available"):
            report["ok"] = False
            report["errors"].append("CUDA is not available to PyTorch")
        if report["checks"]["cuda"].get("vram_gb", 0) < 20:
            report["warnings"].append("Less than 20 GB VRAM detected; use pipeline-type 512 and lower texture sizes.")
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["errors"].append(f"PyTorch import failed: {exc}")

    for mod in ("cumesh", "flex_gemm", "nvdiffrast", "o_voxel", "flash_attn", "xformers", "trimesh", "cv2", "imageio", "transformers"):
        report["checks"][mod] = _check_module(mod)

    attention = os.environ.get("ATTN_BACKEND", "xformers")
    if attention == "flash_attn" and not report["checks"]["flash_attn"]["installed"]:
        report["ok"] = False
        report["errors"].append("ATTN_BACKEND=flash_attn but flash_attn is not installed. Install flash-attn or use xformers.")
    if attention == "xformers" and not report["checks"]["xformers"]["installed"]:
        report["ok"] = False
        report["errors"].append("ATTN_BACKEND=xformers but xformers is not installed. Run setup again.")
    if attention in {"sdpa", "naive"}:
        report["ok"] = False
        report["errors"].append(
            "Sparse attention needs xformers or flash_attn; sdpa/naive only covers dense layers. "
            "Run setup (installs xformers) or use --with-flash-attn."
        )

    for mod in ("cumesh", "flex_gemm", "nvdiffrast", "o_voxel"):
        if not report["checks"][mod]["installed"]:
            report["ok"] = False
            report["errors"].append(f"Required CUDA extension '{mod}' is not installed.")

    try:
        model_path = Path(args.model).expanduser()
        local = model_path.is_dir() and (model_path / "pipeline.json").is_file()
        info: Dict[str, Any] = {
            "value": args.model,
            "local": local,
            "path": str(model_path),
            "missing_checkpoints": [],
            "aux": {},
        }
        if local:
            try:
                config = json.loads((model_path / "pipeline.json").read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                config = {}
                report["ok"] = False
                report["errors"].append(f"pipeline.json is unreadable: {exc}")
            models_cfg = config.get("args", {}).get("models", {})
            for name, value in models_cfg.items():
                if isinstance(value, str) and value.startswith("ckpts/"):
                    json_path = model_path / f"{value}.json"
                    weights_path = model_path / f"{value}.safetensors"
                    if not json_path.is_file() or not weights_path.is_file():
                        info["missing_checkpoints"].append(name)
            if info["missing_checkpoints"]:
                report["ok"] = False
                report["errors"].append(
                    "Missing TRELLIS.2 checkpoints: " + ", ".join(info["missing_checkpoints"])
                )

            aux = model_path / "aux"
            ss_dec = aux / "TRELLIS-image-large" / "ckpts" / "ss_dec_conv3d_16l8_fp16.safetensors"
            dino = aux / "dinov3-vitl16"
            rmbg = aux / "RMBG-2.0"
            info["aux"] = {
                "sparse_structure_decoder": ss_dec.is_file(),
                "dinov3": (dino / "config.json").is_file(),
                "rmbg": (rmbg / "config.json").is_file(),
            }
            if not info["aux"]["sparse_structure_decoder"]:
                report["ok"] = False
                report["errors"].append(
                    "Missing sparse-structure decoder. Run: python3 scripts/blender_skill.py trellis download"
                )
            if not info["aux"]["dinov3"]:
                report["ok"] = False
                report["errors"].append(
                    "Missing DINOv3 image conditioner. Accept the license at "
                    "https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m, "
                    "set HF_TOKEN, then run: python3 scripts/blender_skill.py trellis download"
                )
            if not info["aux"]["rmbg"]:
                report["warnings"].append(
                    "RMBG-2.0 is not local; the bridge will fall back to the public BiRefNet, "
                    "or use alpha input. Accept https://huggingface.co/briaai/RMBG-2.0 to remove the fallback."
                )
        else:
            from huggingface_hub import constants as hf_constants

            cache_root = Path(hf_constants.HF_HUB_CACHE)
            expected = cache_root / ("models--" + args.model.replace("/", "--"))
            info["hf_cache"] = str(cache_root)
            info["hf_dir"] = str(expected)
            info["hf_present"] = expected.exists()
            report["warnings"].append(
                "Model is not a local directory. Run setup --model-dir to download weights into the skill."
            )
        report["checks"]["model"] = info
    except Exception as exc:  # noqa: BLE001
        report["warnings"].append(f"Could not inspect model directory: {exc}")

    _emit_result(report)
    return 0 if report["ok"] else 1


def _install_rembg_fallback() -> None:
    """Fall back to the public BiRefNet when the gated RMBG-2.0 is unavailable.

    TRELLIS.2's default config uses ``briaai/RMBG-2.0``, which is gated. Users who
    have accepted the license keep the default; everyone else gets a working
    non-gated rembg model instead of a pipeline load failure.
    """
    from trellis2.pipelines import rembg

    model_cls = getattr(rembg, "BiRefNet", None)
    if model_cls is None or getattr(model_cls, "_trellis2_fallback_patched", False):
        return

    original_init = model_cls.__init__
    fallback = os.environ.get("TRELLIS2_REMBG_MODEL", "ZhengPeng7/BiRefNet")

    def patched_init(self, model_name: str = "ZhengPeng7/BiRefNet"):
        try:
            original_init(self, model_name)
        except Exception as exc:  # noqa: BLE001
            text = str(exc).lower()
            if any(token in text for token in ("gated", "401", "403", "access")):
                print(
                    f"[TRELLIS2] Could not load rembg model '{model_name}'; "
                    f"falling back to '{fallback}'. ({exc})",
                    flush=True,
                )
                original_init(self, fallback)
            else:
                raise

    model_cls.__init__ = patched_init
    model_cls._trellis2_fallback_patched = True


def _load_pipeline(model: str, low_vram: Optional[bool], pipeline_kind: str):
    _install_rembg_fallback()
    from trellis2.pipelines import Trellis2ImageTo3DPipeline, Trellis2TexturingPipeline

    _progress(10, f"Loading {pipeline_kind} pipeline ({model})")
    try:
        if pipeline_kind == "texture":
            pipeline = Trellis2TexturingPipeline.from_pretrained(model, config_file="texturing_pipeline.json")
        else:
            pipeline = Trellis2ImageTo3DPipeline.from_pretrained(model, config_file="pipeline.json")
    except Exception as exc:  # noqa: BLE001
        text = str(exc).lower()
        if "gated" in text or "403" in text or "401" in text:
            raise RuntimeError(
                "A TRELLIS.2 auxiliary model is gated. Accept the licenses at "
                "https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m and "
                "https://huggingface.co/briaai/RMBG-2.0, set HF_TOKEN, then run "
                "`python3 scripts/blender_skill.py trellis download`."
            ) from exc
        raise
    if low_vram is not None:
        pipeline.low_vram = bool(low_vram)
    pipeline.cuda()
    _progress(20, "Pipeline ready")
    return pipeline


def _export_glb(
    mesh,
    output: Path,
    decimation_target: int,
    texture_size: int,
    remesh: bool,
    remesh_band: float,
    remesh_project: float,
    webp: bool,
    alpha_mode: str,
) -> Dict[str, Any]:
    import o_voxel

    _progress(90, "Extracting UVs and baking PBR texture")
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=mesh.layout,
        voxel_size=mesh.voxel_size,
        aabb=DEFAULT_AABB,
        decimation_target=decimation_target,
        texture_size=texture_size,
        remesh=remesh,
        remesh_band=remesh_band,
        remesh_project=remesh_project,
        verbose=False,
    )

    if alpha_mode and alpha_mode != "opaque":
        try:
            glb.visual.material.alphaMode = alpha_mode.upper()
        except Exception:
            pass

    output.parent.mkdir(parents=True, exist_ok=True)
    glb.export(str(output), extension_webp=webp)
    _progress(98, "GLB written")
    return {"vertices": int(glb.vertices.shape[0]), "faces": int(glb.faces.shape[0])}


def cmd_generate(args: argparse.Namespace) -> int:
    started = time.time()
    output_meta: Dict[str, Any] = {
        "ok": False,
        "task": "generate",
        "model": args.model,
        "image": str(Path(args.image).expanduser().resolve()),
        "seed": args.seed,
        "num_samples": args.num_samples,
        "pipeline_type": args.pipeline_type,
        "decimation_target": args.decimation_target,
        "texture_size": args.texture_size,
        "remesh": not args.no_remesh,
        "alpha_mode": args.alpha_mode,
        "outputs": [],
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    try:
        from PIL import Image

        image_path = Path(args.image).expanduser().resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")
        image = Image.open(image_path)
        _progress(5, f"Image loaded: {image.size[0]}x{image.size[1]}")

        pipeline = _load_pipeline(args.model, args.low_vram, "generate")

        _progress(25, f"Generating {args.num_samples} sample(s) at {args.pipeline_type}")
        meshes = pipeline.run(
            image,
            num_samples=args.num_samples,
            seed=args.seed,
            pipeline_type=args.pipeline_type,
        )
        _progress(85, "Latents decoded")

        for index, mesh in enumerate(meshes):
            if args.simplify_limit and args.simplify_limit > 0:
                mesh.simplify(args.simplify_limit)

            output = _resolve_outputs(args.output, image_path.stem, index, len(meshes))
            stats = _export_glb(
                mesh=mesh,
                output=output,
                decimation_target=args.decimation_target,
                texture_size=args.texture_size,
                remesh=not args.no_remesh,
                remesh_band=args.remesh_band,
                remesh_project=args.remesh_project,
                webp=not args.no_webp,
                alpha_mode=args.alpha_mode,
            )
            output_meta["outputs"].append({"path": str(output), **stats})

        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass

        output_meta["ok"] = True
        output_meta["elapsed_sec"] = round(time.time() - started, 2)
        for item in output_meta["outputs"]:
            _write_sidecar(Path(item["path"]), output_meta)
        _progress(100, "Done")
        _emit_result(output_meta)
        return 0
    except Exception as exc:  # noqa: BLE001
        output_meta["error"] = str(exc)
        output_meta["traceback"] = traceback.format_exc()
        _progress(100, f"Failed: {exc}")
        _emit_result(output_meta)
        return 1


def _load_mesh(path: Path):
    import trimesh

    loaded = trimesh.load(str(path), force="scene")
    if isinstance(loaded, trimesh.Scene):
        if len(loaded.geometry) == 0:
            raise ValueError(f"No geometry found in {path}")
        return loaded.dump(concatenate=True)
    return loaded


def cmd_texture(args: argparse.Namespace) -> int:
    started = time.time()
    output_meta: Dict[str, Any] = {
        "ok": False,
        "task": "texture",
        "model": args.model,
        "image": str(Path(args.image).expanduser().resolve()),
        "mesh": str(Path(args.mesh).expanduser().resolve()),
        "seed": args.seed,
        "resolution": args.resolution,
        "texture_size": args.texture_size,
        "outputs": [],
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    try:
        from PIL import Image

        mesh_path = Path(args.mesh).expanduser().resolve()
        image_path = Path(args.image).expanduser().resolve()
        if not mesh_path.is_file():
            raise FileNotFoundError(f"Mesh not found: {mesh_path}")
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        _progress(5, "Loading mesh")
        mesh = _load_mesh(mesh_path)
        image = Image.open(image_path)
        pipeline = _load_pipeline(args.model, args.low_vram, "texture")

        _progress(30, "Encoding shape and generating PBR texture")
        textured = pipeline.run(
            mesh,
            image,
            seed=args.seed,
            resolution=args.resolution,
            texture_size=args.texture_size,
        )

        output = _resolve_outputs(args.output, mesh_path.stem, 0, 1)
        output.parent.mkdir(parents=True, exist_ok=True)
        _progress(95, "Writing textured GLB")
        textured.export(str(output), extension_webp=not args.no_webp)

        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass

        output_meta["outputs"].append(
            {"path": str(output), "vertices": int(len(textured.vertices)), "faces": int(len(textured.faces))}
        )
        output_meta["ok"] = True
        output_meta["elapsed_sec"] = round(time.time() - started, 2)
        _write_sidecar(output, output_meta)
        _progress(100, "Done")
        _emit_result(output_meta)
        return 0
    except Exception as exc:  # noqa: BLE001
        output_meta["error"] = str(exc)
        output_meta["traceback"] = traceback.format_exc()
        _progress(100, f"Failed: {exc}")
        _emit_result(output_meta)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TRELLIS.2 bridge for Blender")
    parser.add_argument("--vendor-dir", default=os.environ.get("TRELLIS2_VENDOR", str(Path(__file__).resolve().parent.parent / "vendor")))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Validate the TRELLIS.2 environment")
    doctor.set_defaults(func=cmd_doctor)

    gen = sub.add_parser("generate", help="Image-to-3D generation")
    gen.add_argument("--image", required=True)
    gen.add_argument("--output", required=True, help="Output .glb path or directory")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--num-samples", type=int, default=1)
    gen.add_argument(
        "--pipeline-type",
        default="1024_cascade",
        choices=["512", "1024", "1024_cascade", "1536_cascade"],
    )
    gen.add_argument("--decimation-target", type=int, default=250_000)
    gen.add_argument("--texture-size", type=int, default=2048)
    gen.add_argument("--simplify-limit", type=int, default=16_777_216)
    gen.add_argument("--remesh-band", type=float, default=1.0)
    gen.add_argument("--remesh-project", type=float, default=0.0)
    gen.add_argument("--no-remesh", dest="no_remesh", action="store_true")
    gen.add_argument("--remesh", dest="no_remesh", action="store_false")
    gen.add_argument("--no-webp", action="store_true")
    gen.add_argument("--alpha-mode", default="opaque", choices=["opaque", "blend", "mask"])
    gen.add_argument("--low-vram", dest="low_vram", action="store_true", default=None)
    gen.add_argument("--no-low-vram", dest="low_vram", action="store_false")
    gen.set_defaults(func=cmd_generate)

    tex = sub.add_parser("texture", help="PBR texture an existing mesh")
    tex.add_argument("--mesh", required=True)
    tex.add_argument("--image", required=True)
    tex.add_argument("--output", required=True, help="Output .glb path or directory")
    tex.add_argument("--seed", type=int, default=42)
    tex.add_argument("--resolution", type=int, default=1024, choices=[512, 1024])
    tex.add_argument("--texture-size", type=int, default=2048)
    tex.add_argument("--no-webp", action="store_true")
    tex.add_argument("--low-vram", dest="low_vram", action="store_true", default=None)
    tex.add_argument("--no-low-vram", dest="low_vram", action="store_false")
    tex.set_defaults(func=cmd_texture)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _bootstrap_vendor(args.vendor_dir)
    if args.command != "doctor":
        os.environ.setdefault("ATTN_BACKEND", "sdpa")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
