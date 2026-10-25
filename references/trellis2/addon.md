# TRELLIS.2 Blender add-on

The vendored add-on is an optional interactive UI. Agents should use the MCP or
the CLI; the add-on launches the same bridge.

## Install

```bash
python3 scripts/blender_skill.py setup --with-trellis-addon
```

Or install manually: `Edit > Preferences > Get Extensions > Install from Disk`,
choose `trellis/addon/dist/trellis2_bridge-*.zip`, then enable **TRELLIS.2
Bridge**.

## Preferences

`Edit > Preferences > Add-ons > TRELLIS.2 Bridge`

| Preference | Default | Notes |
|---|---|---|
| Vendor directory | resolved by the guide | Must contain `trellis2/` |
| Python executable | guide TRELLIS venv | Leave empty to resolve automatically |
| Output directory | `<home>/outputs` | GLB + logs |
| Model | local weights dir | Falls back to `microsoft/TRELLIS.2-4B` |
| HF_HOME | empty | Optional cache override |
| Quality | `1024_cascade` | 512 / 1024 / cascade |
| Texture size | `2048` | 1K / 2K / 4K |
| Decimation target | `250000` | Vertex target |
| Remesh | on | Recommended |
| Apply alpha | on | Wire base-color alpha after import |
| Low VRAM mode | on | Recommended below 24 GB |
| Attention backend | `flash_attn` | Switch to `sdpa` if unavailable |
| Import scale | `1.0` | Applied after import |
| Keep job logs | on | Logs next to outputs |

## Panel

3D Viewport → `N` → **TRELLIS.2**.

- **Check Setup** runs doctor and stores the report on the scene.
- **Show Setup Report** reports the last report text.
- **Image to 3D** uses the scene image path and quality settings.
- **Texture Selected Mesh** exports the selection, runs texturing, imports the
  result, and optionally fits it back to the original bounds.
- **Import Last Result** re-imports the last output.
- **Open Last Log** opens the subprocess log.

## Job lifecycle

1. Operator validates paths and builds the bridge command.
2. `subprocess.Popen` runs with the TRELLIS venv and a log file.
3. A `bpy.app.timers` callback polls every 0.5 s and parses
   `TRELLIS2_PROGRESS` for the progress bar.
4. On success the add-on reads the sidecar, imports every output, moves objects
   into `COL_TRELLIS2`, names them `SM_TRELLIS2_<stem>_<index>`, stores
   provenance, wires alpha, and optionally fits texture results.
5. On failure the status bar shows the error; the log holds the traceback.

The add-on never imports torch. Cancelling sends SIGTERM to the process group.

## Texturing caveat

The texturing pipeline normalizes the selected mesh into a unit AABB. **Fit To
Original** rescales and recenters the result to the pre-export bounds. It cannot
recover non-uniform deformation or exact rotation; for precise placement,
texture a mesh that is already normalized, or re-place the result manually.

## Known limitations

- GLB alpha is exported `OPAQUE`; the add-on optionally wires it after import.
- Normal maps are not generated.
- No multi-view conditioning.
- Remesh output is dense uniform topology; retopo/decimate before shipping.
- One GPU job at a time is enforced in the UI.
