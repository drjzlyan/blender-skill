import json
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from . import job


class TRELLIS2_OT_Generate(Operator):
    bl_idname = "trellis2.generate"
    bl_label = "Generate 3D Asset"
    bl_description = "Generate a PBR 3D asset from the reference image with TRELLIS.2"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return not job.is_running()

    def execute(self, context):
        try:
            job.start_generate(context)
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, str(exc))
            context.scene.trellis2_status = f"Error: {exc}"
            return {"CANCELLED"}
        return {"FINISHED"}


class TRELLIS2_OT_TextureSelected(Operator):
    bl_idname = "trellis2.texture_selected"
    bl_label = "Texture Selected Mesh"
    bl_description = "Generate new PBR textures for the selected mesh using the reference image"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return not job.is_running() and any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        try:
            job.start_texture(context)
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, str(exc))
            context.scene.trellis2_status = f"Error: {exc}"
            return {"CANCELLED"}
        return {"FINISHED"}


class TRELLIS2_OT_Cancel(Operator):
    bl_idname = "trellis2.cancel"
    bl_label = "Cancel Job"
    bl_description = "Stop the running TRELLIS.2 job"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return job.is_running()

    def execute(self, context):
        job.cancel(context)
        return {"FINISHED"}


class TRELLIS2_OT_CheckSetup(Operator):
    bl_idname = "trellis2.check_setup"
    bl_label = "Check Setup"
    bl_description = "Verify the TRELLIS.2 environment, CUDA extensions, and model cache"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            report = job.run_doctor(context)
        except Exception as exc:  # noqa: BLE001
            context.scene["trellis2_doctor_ok"] = False
            context.scene["trellis2_doctor"] = json.dumps({"ok": False, "error": str(exc)}, indent=2)
            context.scene.trellis2_status = f"Setup check failed: {exc}"
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        context.scene["trellis2_doctor_ok"] = bool(report.get("ok"))
        context.scene["trellis2_doctor"] = json.dumps(report, indent=2)
        if report.get("ok"):
            device = report.get("checks", {}).get("cuda", {}).get("device", "GPU")
            context.scene.trellis2_status = f"Setup OK - {device}"
            self.report({"INFO"}, "TRELLIS.2 setup is ready")
        else:
            errors = report.get("errors") or [report.get("error", "Unknown error")]
            context.scene.trellis2_status = "Setup failed: " + "; ".join(errors)[:220]
            self.report({"ERROR"}, "; ".join(errors)[:400])
        return {"FINISHED"}


class TRELLIS2_OT_ImportLatest(Operator):
    bl_idname = "trellis2.import_latest"
    bl_label = "Import Last Result"
    bl_description = "Import the most recently generated GLB into the scene"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        path = context.scene.trellis2_last_output
        return bool(path) and Path(path).is_file()

    def execute(self, context):
        path = context.scene.trellis2_last_output
        try:
            objects = job.import_last(context, path)
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Imported {len(objects)} object(s)")
        return {"FINISHED"}


class TRELLIS2_OT_OpenLog(Operator):
    bl_idname = "trellis2.open_log"
    bl_label = "Open Last Log"
    bl_description = "Open the log of the last TRELLIS.2 job"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        path = job.last_log_path()
        return path is not None and path.is_file()

    def execute(self, context):
        path = job.last_log_path()
        if path is None:
            return {"CANCELLED"}
        try:
            bpy.ops.wm.path_open(filepath=str(path))
        except Exception:  # noqa: BLE001
            self.report({"INFO"}, str(path))
        return {"FINISHED"}


class TRELLIS2_OT_ShowDoctor(Operator):
    bl_idname = "trellis2.show_doctor"
    bl_label = "Show Setup Report"
    bl_description = "Show the last setup report"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get("trellis2_doctor"))

    def execute(self, context):
        report = context.scene.get("trellis2_doctor", "")
        self.report({"INFO"}, report[:800] if isinstance(report, str) else str(report))
        return {"FINISHED"}


CLASSES = (
    TRELLIS2_OT_Generate,
    TRELLIS2_OT_TextureSelected,
    TRELLIS2_OT_Cancel,
    TRELLIS2_OT_CheckSetup,
    TRELLIS2_OT_ImportLatest,
    TRELLIS2_OT_OpenLog,
    TRELLIS2_OT_ShowDoctor,
)
