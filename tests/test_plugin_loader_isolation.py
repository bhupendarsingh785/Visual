"""Regression tests for namespace isolation and atomic plugin tool registration."""
import ast
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


class PluginLoaderIsolationTests(unittest.TestCase):
    def test_plugins_get_private_globals_and_failed_plugins_publish_nothing(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "visual.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "load_plugins")
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "plugins"
            plugin_dir.mkdir()
            (plugin_dir / "a_good.py").write_text(
                "PLUGIN_PRIVATE_VALUE = 42\n"
                "@tool('good tool', {})\n"
                "def good_tool(): return PLUGIN_PRIVATE_VALUE\n",
                encoding="utf-8",
            )
            (plugin_dir / "b_bad.py").write_text(
                "@tool('partial tool', {})\n"
                "def partial_tool(): return 'must not publish'\n"
                "raise RuntimeError('load failed after decorator')\n",
                encoding="utf-8",
            )
            host = {
                "PLUGIN_ERRORS": {}, "PLUGINS": str(plugin_dir),
                "TOOLS": {}, "RISKY": set(), "os": os, "sys": sys, "re": re,
            }
            module = ast.Module(body=[function], type_ignores=[])
            exec(compile(module, str(root / "visual.py"), "exec"), host)
            loaded = host["load_plugins"]()
            self.assertEqual(loaded, ["a_good.py"])
            self.assertEqual(set(host["TOOLS"]), {"good_tool"})
            self.assertIn("b_bad.py", host["PLUGIN_ERRORS"])
            self.assertNotIn("PLUGIN_PRIVATE_VALUE", host)
            self.assertEqual(host["TOOLS"]["good_tool"]["fn"](), 42)
            self.assertEqual(host["TOOLS"]["good_tool"]["fn"].__globals__["PLUGIN_PRIVATE_VALUE"], 42)

    def test_duplicate_tool_names_fail_atomically(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "visual.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "load_plugins")
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "plugins"
            plugin_dir.mkdir()
            (plugin_dir / "a_first.py").write_text("@tool('first', {})\ndef same(): return 1\n", encoding="utf-8")
            (plugin_dir / "b_second.py").write_text("@tool('second', {})\ndef same(): return 2\n", encoding="utf-8")
            host = {"PLUGIN_ERRORS": {}, "PLUGINS": str(plugin_dir), "TOOLS": {}, "RISKY": set(), "os": os, "sys": sys, "re": re}
            exec(compile(ast.Module(body=[function], type_ignores=[]), str(root / "visual.py"), "exec"), host)
            self.assertEqual(host["load_plugins"](), ["a_first.py"])
            self.assertIn("b_second.py", host["PLUGIN_ERRORS"])
            self.assertEqual(host["TOOLS"]["same"]["fn"](), 1)


if __name__ == "__main__":
    unittest.main()
