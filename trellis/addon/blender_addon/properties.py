import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty


def register():
    Scene = bpy.types.Scene

    Scene.trellis2_image_path = StringProperty(
        name="Image",
        description="Reference image for image-to-3D generation",
        subtype="FILE_PATH",
        default="",
    )
    Scene.trellis2_texture_image_path = StringProperty(
        name="Reference Image",
        description="Image that drives the PBR texture for the selected mesh",
        subtype="FILE_PATH",
        default="",
    )
    Scene.trellis2_output_dir = StringProperty(
        name="Output Directory",
        description="Leave empty to use the add-on preference",
        subtype="DIR_PATH",
        default="",
    )
    Scene.trellis2_pipeline_type = EnumProperty(
        name="Quality",
        items=[
            ("512", "Fast (512)", "Fastest, lowest VRAM"),
            ("1024", "Balanced (1024)", "Single-stage 1024"),
            ("1024_cascade", "High (1024 cascade)", "Recommended"),
            ("1536_cascade", "Ultra (1536 cascade)", "High VRAM"),
        ],
        default="1024_cascade",
    )
    Scene.trellis2_seed = IntProperty(name="Seed", default=42, min=0, max=2**31 - 1)
    Scene.trellis2_num_samples = IntProperty(name="Samples", default=1, min=1, max=8)
    Scene.trellis2_decimation = IntProperty(
        name="Decimation Target", default=250_000, min=1_000, max=16_000_000
    )
    Scene.trellis2_texture_size = EnumProperty(
        name="Texture",
        items=[("1024", "1K", ""), ("2048", "2K", ""), ("4096", "4K", "")],
        default="2048",
    )
    Scene.trellis2_remesh = BoolProperty(name="Remesh", default=True)
    Scene.trellis2_apply_alpha = BoolProperty(name="Apply Alpha", default=True)
    Scene.trellis2_fit_to_original = BoolProperty(
        name="Fit To Original",
        description="Scale and center textured results to the original object's bounds",
        default=True,
    )
    Scene.trellis2_import_scale = FloatProperty(name="Import Scale", default=1.0, min=0.001, max=1000.0)
    Scene.trellis2_name_prefix = StringProperty(name="Name Prefix", default="SM_TRELLIS2")
    Scene.trellis2_status = StringProperty(name="Status", default="Idle")
    Scene.trellis2_progress = FloatProperty(name="Progress", default=0.0, min=0.0, max=1.0)
    Scene.trellis2_running = BoolProperty(name="Running", default=False)
    Scene.trellis2_last_output = StringProperty(name="Last Output", default="")


def unregister():
    Scene = bpy.types.Scene
    for name in (
        "trellis2_image_path",
        "trellis2_texture_image_path",
        "trellis2_output_dir",
        "trellis2_pipeline_type",
        "trellis2_seed",
        "trellis2_num_samples",
        "trellis2_decimation",
        "trellis2_texture_size",
        "trellis2_remesh",
        "trellis2_apply_alpha",
        "trellis2_fit_to_original",
        "trellis2_import_scale",
        "trellis2_name_prefix",
        "trellis2_status",
        "trellis2_progress",
        "trellis2_running",
        "trellis2_last_output",
    ):
        if hasattr(Scene, name):
            delattr(Scene, name)
