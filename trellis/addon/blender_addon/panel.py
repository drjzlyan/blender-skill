import bpy
from bpy.types import Panel

from . import job


class TRELLIS2_PT_Main(Panel):
    bl_label = "TRELLIS.2"
    bl_idname = "TRELLIS2_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TRELLIS.2"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        header = layout.box()
        row = header.row(align=True)
        if scene.trellis2_running:
            row.label(text=scene.trellis2_status, icon="SORTTIME")
        else:
            icon = "CHECKMARK" if scene.get("trellis2_doctor_ok") else "INFO"
            row.label(text=scene.trellis2_status, icon=icon)

        if scene.trellis2_running:
            header.progress(factor=scene.trellis2_progress, type="BAR", text=f"{int(scene.trellis2_progress * 100)}%")
            header.operator("trellis2.cancel", icon="CANCEL")
        else:
            row = header.row(align=True)
            row.operator("trellis2.check_setup", icon="CHECKMARK")
            row.operator("trellis2.show_doctor", text="", icon="INFO")

        box = layout.box()
        box.label(text="Image to 3D", icon="IMAGE_DATA")
        box.prop(scene, "trellis2_image_path", text="")
        col = box.column(align=True)
        col.prop(scene, "trellis2_pipeline_type")
        row = col.row(align=True)
        row.prop(scene, "trellis2_seed")
        row.prop(scene, "trellis2_num_samples")
        row = col.row(align=True)
        row.prop(scene, "trellis2_decimation")
        row.prop(scene, "trellis2_texture_size")
        row = col.row(align=True)
        row.prop(scene, "trellis2_remesh")
        row.prop(scene, "trellis2_apply_alpha")
        box.operator("trellis2.generate", icon="MESH_MONKEY", text="Generate Asset")

        box = layout.box()
        box.label(text="Texture Selected Mesh", icon="TEXTURE")
        box.prop(scene, "trellis2_texture_image_path", text="")
        box.prop(scene, "trellis2_fit_to_original")
        box.operator("trellis2.texture_selected", icon="TPAINT_HLT", text="Texture Selected")

        box = layout.box()
        box.label(text="Import", icon="IMPORT")
        row = box.row(align=True)
        row.prop(scene, "trellis2_name_prefix")
        row.prop(scene, "trellis2_import_scale")
        box.prop(scene, "trellis2_output_dir", text="Output")
        row = box.row(align=True)
        row.operator("trellis2.import_latest", icon="IMPORT")
        row.operator("trellis2.open_log", icon="TEXT")

        prefs = context.preferences.addons.get(__package__)
        if prefs is not None and prefs.preferences.model:
            col = layout.column()
            col.scale_y = 0.8
            col.label(text=f"Model: {prefs.preferences.model}", icon="FILE_CACHE")
            col.label(text=f"Python: {prefs.preferences.resolved_python()}", icon="CONSOLE")


CLASSES = (TRELLIS2_PT_Main,)
