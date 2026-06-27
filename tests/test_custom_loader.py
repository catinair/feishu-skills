#!/usr/bin/env python3
"""Tests for custom skill/script loader."""

import tempfile
import unittest
from pathlib import Path


class TestCustomLoader(unittest.TestCase):
    def _load_loader(self):
        import importlib.util
        loader_path = Path(__file__).parent.parent / "feishu_common" / "_custom_loader.py"
        spec = importlib.util.spec_from_file_location("_custom_loader", loader_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_empty_custom_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "custom").mkdir()
            loader = self._load_loader()
            result = loader.load_custom_skills(custom_dir=root / "custom")
            self.assertEqual(result, {"scripts": [], "skills": []})

    def test_discovers_python_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            custom = root / "custom"
            custom.mkdir()
            script = custom / "hello.py"
            script.write_text('"""My hello script."""\nprint("hello")\n', encoding="utf-8")
            loader = self._load_loader()
            result = loader.load_custom_skills(custom_dir=custom)
            self.assertEqual(len(result["scripts"]), 1)
            self.assertEqual(result["scripts"][0]["name"], "hello")
            self.assertEqual(result["scripts"][0]["description"], "My hello script.")

    def test_discovers_sub_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            custom = root / "custom"
            custom.mkdir()
            skill_dir = custom / "my-workflow"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                "---\nname: my-workflow\nversion: 1.0.0\ndescription: A custom workflow\n---\n",
                encoding="utf-8",
            )
            loader = self._load_loader()
            result = loader.load_custom_skills(custom_dir=custom)
            self.assertEqual(len(result["skills"]), 1)
            self.assertEqual(result["skills"][0]["name"], "my-workflow")
            self.assertEqual(result["skills"][0]["version"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
