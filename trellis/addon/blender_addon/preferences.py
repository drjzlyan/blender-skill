import os
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty


def default_vendor_dir() -> str:
    return os.environ.get("TRELLIS2_VENDOR", "")


def default_output_dir() -> str:
    env = os.environ.get("TRELLIS2_OUTPUT")
    if env:
        return env
    home = os.environ.get("BLENDER_SKILL_HOME")
    return str(Path(home) / "outputs") if home else ""


class TRELLIS2_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    vendor_dir: StringProperty(
        name="Vendor Directory",
        description="Path to the skill's trellis/vendor directory",
        subtype="DIR_PATH",
        default=default_vendor_dir(),
    )
    python_executable: StringProperty(
        name="Python Executable",
        description="Python from the skill's TRELLIS venv (set by setup)",
        subtype="FILE_PATH",
        default=os.environ.get("TRELLIS2_PYTHON", ""),
    )
    output_dir: StringProperty(
        name="Output Directory",
        description="Where generated GLB files and logs are written",
        subtype="DIR_PATH",
        default=default_output_dir(),
    )
    model: StringProperty(
        name="Model",
        description="Local TRELLIS.2-4B directory or Hugging Face model id",
        default=os.environ.get("TRELLIS2_MODEL", "microsoft/TRELLIS.2-4B"),
    )
    hf_home: StringProperty(
        name="HF_HOME",
        description="Optional Hugging Face cache directory (leave empty to use the default)",
        subtype="DIR_PATH",
        default="",
    )
    pipeline_type: EnumProperty(
        name="Quality",
        items=[
            ("512", "Fast (512)", "Fastest, lowest VRAM"),
            ("1024", "Balanced (1024)", "Single-stage 1024"),
            ("1024_cascade", "High (1024 cascade)", "Best quality/VRAM balance"),
            ("1536_cascade", "Ultra (1536 cascade)", "Highest quality, needs lots of VRAM"),
        ],
        default="1024_cascade",
    )
    texture_size: EnumProperty(
        name="Texture Size",
        items=[
            ("1024", "1K", "1024 x 1024"),
            ("2048", "2K", "2048 x 2048"),
            ("4096", "4K", "4096 x 4096"),
        ],
        default="2048",
    )
    decimation_target: IntProperty(
        name="Decimation Target",
        description="Target vertex count for the exported GLB",
        default=250_000,
        min=1_000,
        max=16_000_000,
    )
    remesh: BoolProperty(
        name="Remesh",
        description="Rebuild topology during GLB extraction (recommended for Blender)",
        default=True,
    )
    apply_alpha: BoolProperty(
        name="Apply Alpha",
        description="Connect the base-color texture alpha to Principled Alpha after import",
        default=True,
    )
    low_vram: BoolProperty(
        name="Low VRAM Mode",
        description="Offload models between stages. Keep enabled on 24 GB GPUs",
        default=True,
    )
    attn_backend: EnumProperty(
        name="Attention Backend",
        items=[
            ("flash_attn", "Flash Attention", "Fastest; requires flash-attn"),
            ("sdpa", "PyTorch SDPA", "No extra dependency; slower"),
            ("xformers", "xFormers", "Requires xformers"),
        ],
        default="flash_attn",
    )
    default_scale: FloatProperty(
        name="Import Scale",
        description="Uniform scale applied to generated objects",
        default=1.0,
        min=0.001,
        max=1000.0,
    )
    keep_logs: BoolProperty(
        name="Keep Job Logs",
        description="Keep subprocess logs next to generated assets",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        box = layout.box()
        box.label(text="TRELLIS.2 Environment", icon="TOOL_SETTINGS")
        box.prop(self, "vendor_dir")
        box.prop(self, "python_executable")
        box.prop(self, "model")
        box.prop(self, "hf_home")
        box.prop(self, "attn_backend")
        box.prop(self, "low_vram")

        box = layout.box()
        box.label(text="Defaults", icon="PREFERENCES")
        box.prop(self, "output_dir")
        box.prop(self, "pipeline_type")
        box.prop(self, "texture_size")
        box.prop(self, "decimation_target")
        box.prop(self, "remesh")
        box.prop(self, "apply_alpha")
        box.prop(self, "default_scale")
        box.prop(self, "keep_logs")

    def resolved_python(self) -> str:
        if self.python_executable:
            return bpy.path.abspath(self.python_executable)
        env = os.environ.get("TRELLIS2_PYTHON")
        if env:
            return env
        home = os.environ.get("BLENDER_SKILL_HOME")
        if home:
            return str(Path(home) / "venvs" / "trellis" / "bin" / "python")
        return ""

    def resolved_repo(self) -> Path:
        return Path(bpy.path.abspath(self.vendor_dir)).expanduser()

    def resolved_bridge(self) -> Path:
        env = os.environ.get("TRELLIS2_BRIDGE")
        if env:
            return Path(env).expanduser()
        vendor = self.resolved_repo()
        for candidate in (
            vendor.parent / "bridge" / "trellis2_bridge.py",
            vendor.parent.parent / "trellis" / "bridge" / "trellis2_bridge.py",
        ):
            if candidate.is_file():
                return candidate
        return vendor.parent / "bridge" / "trellis2_bridge.py"


def get_preferences(context) -> TRELLIS2_AddonPreferences:
    addon = context.preferences.addons.get(__package__)
    if addon is None:
        raise RuntimeError("TRELLIS.2 add-on preferences are unavailable")
    return addon.preferences
