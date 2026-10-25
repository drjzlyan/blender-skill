import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_single_skill_manifest(self):
        manifests = list(ROOT.rglob("SKILL.md"))
        self.assertEqual(manifests, [ROOT / "SKILL.md"], "only the root SKILL.md may be installable")

    def test_manifest_identity(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: blender-skill", text)
        self.assertIn("license: MIT", text)
        self.assertIn("doctor", text)
        self.assertIn("trellis2_generate", text)
        self.assertIn("references/index.md", text)

    def test_no_topcoder_bundle(self):
        self.assertFalse((ROOT / "references" / "topcoder").exists())
        self.assertFalse((ROOT / "references" / "library" / "core" / "topcoder").exists())

    def test_no_legacy_skill_references(self):
        legacy = ("blender-modeler", "blender-director", "blender-rendering", "blender-scene-setup",
                  "blender-skill-harmonizer", "references/skills/", "references/extra/")
        offenders = []
        for path in list((ROOT / "references").rglob("*.md")) + [ROOT / "SKILL.md", ROOT / "README.md"]:
            if path.name == "THIRD_PARTY_NOTICES.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in legacy:
                if needle in text:
                    offenders.append(str(path.relative_to(ROOT)))
                    break
        self.assertEqual(offenders, [], f"legacy skill references in: {offenders[:10]}")

    def test_corpus_present(self):
        index = (ROOT / "references" / "index.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(index.count("### "), 140)
        guides = list((ROOT / "references" / "library" / "core").glob("*/guide.md"))
        self.assertEqual(len(guides), 94)
        self.assertTrue((ROOT / "references" / "library" / "el4cteo" / "guides").is_dir())
        self.assertTrue((ROOT / "references" / "library" / "roble3" / "guides").is_dir())
        self.assertTrue((ROOT / "references" / "library" / "majid" / "guides").is_dir())
        self.assertFalse((ROOT / "references" / "skills").exists())
        self.assertFalse((ROOT / "references" / "extra").exists())

    def test_attribution(self):
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for needle in ("arjun988/blender-skills", "EL4CTEO/blender-skills", "RobLe3/cc-blender-skill",
                       "majidmanzarpour/blender-game-skills", "microsoft/TRELLIS.2"):
            self.assertIn(needle, notices)
        self.assertTrue((ROOT / "references" / "library" / "core" / "LICENSE").is_file())

    def test_no_machine_paths(self):
        patterns = [re.compile(r"/home/[A-Za-z0-9._-]+"), re.compile(r"/Users/[A-Za-z0-9._-]+")]
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name == "test_packaging.py":
                continue
            if "third_party" in str(path) or "__pycache__" in str(path):
                continue
            if path.suffix.lower() not in {".md", ".py", ".json", ".toml", ".sh", ".ps1", ".txt", ".yml", ".yaml", ".cfg"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(pattern.search(text) for pattern in patterns):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f"machine paths or identity in: {offenders[:10]}")

    def test_trellis_vendor_present(self):
        self.assertTrue((ROOT / "trellis" / "vendor" / "trellis2" / "pipelines").is_dir())
        self.assertTrue((ROOT / "trellis" / "vendor" / "o-voxel" / "o_voxel").is_dir())
        self.assertTrue((ROOT / "trellis" / "bridge" / "trellis2_bridge.py").is_file())
        self.assertTrue((ROOT / "trellis" / "LICENSE").is_file())

    def test_examples_exist(self):
        examples = list((ROOT / "examples").glob("*.md"))
        self.assertGreaterEqual(len(examples), 4)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for example in examples:
            self.assertIn(example.name, readme)


if __name__ == "__main__":
    unittest.main()
