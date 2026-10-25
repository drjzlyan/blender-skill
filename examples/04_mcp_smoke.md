# Example 4 — MCP smoke test

**Goal:** prove the skill, MCP, and add-on are wired correctly.

## 1. Check the machine

```bash
python3 scripts/blender_skill.py doctor
```

Require `ok: true` for Blender, Python, and the MCP executable. Treat GPU/TRELLIS
as separate: manual Blender work does not need CUDA.

## 2. Start Blender

1. Open Blender 4.5+.
2. `N` sidebar → **Blender Skill** → **Start Server**.
3. The panel shows the host and port.

## 3. Call the MCP

```json
{"tool": "blender_skill_status"}
```

Expected: Blender version, connection state, GPU profile, TRELLIS paths.

```json
{"tool": "execute_blender_code", "code": "import bpy\nresult = {'objects': len(bpy.data.objects), 'version': bpy.app.version_string}"}
```

## 4. Inspect and capture

```json
{"tool": "get_objects_summary"}
{"tool": "get_screenshot_of_window_as_json"}
{"tool": "get_screenshot_of_area_as_image", "area_ui_type": "VIEW_3D"}
```

## 5. Render

```json
{"tool": "render_thumbnail_to_path", "path": "/tmp/blender_skill_smoke.png"}
```

## 6. Automated check

```bash
python3 scripts/blender_skill.py test fast
python3 scripts/blender_skill.py test mcp
```

`test fast` is GPU-free. `test mcp` creates a tagged cube, verifies the scene
and a screenshot, renders a thumbnail if a camera exists, then removes the test
object.
