# blender-skill-mcp

MIT MCP server for the `blender-skill` agent skill.

```bash
pip install -e .
blender-skill-mcp
```

The server speaks stdio MCP and connects to the Blender add-on over
`127.0.0.1:9876` by default. Configure with:

| Variable | Default |
|---|---|
| `BLENDER_SKILL_HOME` | `~/.local/share/blender-skill` |
| `BLENDER_SKILL_CONFIG` | `~/.config/blender-skill/config.json` |
| `BLENDER_SKILL_ROOT` | installed skill root |
| `BLENDER_SKILL_MCP_HOST` | `127.0.0.1` |
| `BLENDER_SKILL_MCP_PORT` | `9876` |
| `BLENDER_SKILL_MCP_TOKEN` | empty |

Tools cover execution, scene inspection, screenshots, viewport navigation,
rendering, live API documentation, TRELLIS.2 generation, and diagnostics.
