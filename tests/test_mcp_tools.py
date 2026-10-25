import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def has_mcp() -> bool:
    try:
        return importlib.util.find_spec("mcp.server.fastmcp") is not None
    except ModuleNotFoundError:
        return False


@unittest.skipUnless(has_mcp(), "mcp SDK not installed in this interpreter")
class McpToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "mcp"))
        from blender_skill_mcp.server import create_server

        cls.server = create_server()
        cls.tools = {tool.name for tool in cls.server._tool_manager.list_tools()}

    def test_required_tools(self):
        required = {
            "execute_blender_code",
            "get_objects_summary",
            "get_object_detail_summary",
            "get_blendfile_summary_datablocks",
            "get_screenshot_of_window_as_image",
            "get_screenshot_of_area_as_image",
            "render_viewport_to_path",
            "render_thumbnail_to_path",
            "get_python_api_docs",
            "search_api_docs",
            "search_manual_docs",
            "trellis2_doctor",
            "trellis2_generate",
            "trellis2_texture",
            "trellis2_import",
            "blender_skill_status",
        }
        missing = required - self.tools
        self.assertEqual(missing, set(), f"missing MCP tools: {sorted(missing)}")

    def test_tool_count(self):
        self.assertGreaterEqual(len(self.tools), 20)


if __name__ == "__main__":
    unittest.main()
