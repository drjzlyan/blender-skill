import bpy

from . import job, operators, panel, preferences, properties


def register():
    for cls in (
        preferences.TRELLIS2_AddonPreferences,
        *operators.CLASSES,
        *panel.CLASSES,
    ):
        bpy.utils.register_class(cls)
    properties.register()


def unregister():
    if job.is_running():
        try:
            job.cancel(bpy.context)
        except Exception:  # noqa: BLE001
            pass
    try:
        properties.unregister()
    except Exception:
        pass
    for cls in (
        *panel.CLASSES,
        *operators.CLASSES,
        preferences.TRELLIS2_AddonPreferences,
    ):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
