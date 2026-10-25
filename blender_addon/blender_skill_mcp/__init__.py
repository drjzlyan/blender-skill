"""Blender Skill MCP add-on.

An independent MIT implementation of a local MCP bridge for Blender. It exposes
a small socket server that the ``blender-skill-mcp`` server drives. No code is
imported from Blender Lab's GPL add-on.
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences, Operator, Panel

try:
    from . import server as _server
except ImportError:  # legacy add-on import
    import server as _server  # type: ignore

bl_info = {
    "name": "Blender Skill MCP",
    "author": "blender-skill contributors",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "3D View > Sidebar > Blender Skill",
    "description": "Local MCP bridge for the blender-skill agent skill",
    "category": "Development",
    "license": "MIT",
}

ADDON_ID = __package__ or "blender_skill_mcp"


def _prefs(context=None) -> AddonPreferences | None:
    try:
        return bpy.context.preferences.addons[ADDON_ID].preferences
    except Exception:
        return None


class BLENDER_SKILL_OT_start(Operator):
    bl_idname = "blender_skill.start_server"
    bl_label = "Start Server"
    bl_description = "Start the local MCP bridge"

    def execute(self, context):
        prefs = _prefs(context)
        if prefs is None:
            self.report({"ERROR"}, "Preferences unavailable")
            return {"CANCELLED"}
        ok, message = _server.SERVER.start(prefs.host, prefs.port, prefs.token)
        self.report({"INFO" if ok else "ERROR"}, message)
        return {"FINISHED"} if ok else {"CANCELLED"}


class BLENDER_SKILL_OT_stop(Operator):
    bl_idname = "blender_skill.stop_server"
    bl_label = "Stop Server"
    bl_description = "Stop the local MCP bridge"

    def execute(self, context):
        _server.SERVER.stop()
        self.report({"INFO"}, "Stopped")
        return {"FINISHED"}


class BLENDER_SKILL_PT_panel(Panel):
    bl_label = "Blender Skill MCP"
    bl_idname = "BLENDER_SKILL_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Blender Skill"

    def draw(self, context):
        layout = self.layout
        prefs = _prefs(context)
        running = _server.SERVER.running
        box = layout.box()
        box.label(text=f"Status: {'running' if running else 'stopped'}", icon="PLAY" if running else "PAUSE")
        if running:
            box.label(text=f"{_server.SERVER.host}:{_server.SERVER.port}")
        elif _server.SERVER.last_error:
            box.label(text=_server.SERVER.last_error[:60], icon="ERROR")
        row = layout.row(align=True)
        row.operator("blender_skill.start_server", icon="PLAY")
        row.operator("blender_skill.stop_server", icon="PAUSE")
        if prefs is not None:
            layout.prop(prefs, "host")
            layout.prop(prefs, "port")
            layout.prop(prefs, "auto_start")
            layout.prop(prefs, "token")
        layout.label(text="Point the blender-skill MCP at this port.", icon="INFO")


class BLENDER_SKILL_Preferences(AddonPreferences):
    bl_idname = ADDON_ID

    host: StringProperty(
        name="Host",
        default="127.0.0.1",
        description="Interface to bind; keep this on localhost",
    )
    port: IntProperty(
        name="Port",
        default=9876,
        min=1,
        max=65535,
        description="TCP port for the MCP bridge",
    )
    token: StringProperty(
        name="Token",
        default="",
        subtype="PASSWORD",
        description="Optional shared token required in every request",
    )
    auto_start: BoolProperty(
        name="Auto Start",
        default=True,
        description="Start the bridge when Blender loads",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "host")
        layout.prop(self, "port")
        layout.prop(self, "token")
        layout.prop(self, "auto_start")
        layout.label(text="Bind to 127.0.0.1 unless you fully trust the network.", icon="ERROR")


CLASSES = (
    BLENDER_SKILL_Preferences,
    BLENDER_SKILL_OT_start,
    BLENDER_SKILL_OT_stop,
    BLENDER_SKILL_PT_panel,
)


def register():
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    if bpy.app.background:
        return
    prefs = _prefs()
    if prefs is not None and prefs.auto_start:
        _server.SERVER.start(prefs.host, prefs.port, prefs.token)


def unregister():
    _server.SERVER.stop()
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
