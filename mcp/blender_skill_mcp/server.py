"""MCP server entry point for the blender-skill bridge."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import paths
from .tools import register_tools

INSTRUCTIONS = """Local Blender control for the blender-skill agent skill.

Before the first call, enable the "Blender Skill MCP" add-on in Blender and press
Start Server. Use execute_blender_code for live scene work; prefer the scoped
scene/render/screenshot tools when they fit. TRELLIS.2 tools run a separate
CUDA process and may take minutes. Never expose this server beyond localhost.
"""


def create_server() -> FastMCP:
    try:
        mcp = FastMCP("blender-skill", instructions=INSTRUCTIONS)
    except TypeError:
        mcp = FastMCP("blender-skill")
    register_tools(mcp)
    return mcp


def main() -> None:
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
