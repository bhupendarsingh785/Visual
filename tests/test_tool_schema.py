"""Regression tests for VISUAL's core tool schema decorator (no runtime import)."""
import ast
import unittest
from pathlib import Path


class ToolSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "visual.py"
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        node = next(
            item for item in tree.body
            if isinstance(item, ast.FunctionDef) and item.name == "tool"
        )
        cls.namespace = {"TOOLS": {}, "RISKY": set()}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), cls.namespace)

    def test_optional_flag_is_not_removed_from_caller_schema(self):
        params = {
            "required_value": {"type": "string", "description": "required"},
            "optional_value": {"type": "string", "description": "optional", "optional": True},
        }
        decorate = self.namespace["tool"]("schema test", params)

        @decorate
        def sample_tool(required_value, optional_value=None):
            return required_value, optional_value

        schema = self.namespace["TOOLS"]["sample_tool"]["schema"]["function"]["parameters"]
        self.assertEqual(schema["required"], ["required_value"])
        self.assertTrue(params["optional_value"]["optional"])
        self.assertIn("optional", params["optional_value"])

    def test_schema_properties_preserve_optional_metadata(self):
        params = {"maybe": {"type": "string", "optional": True}}
        decorate = self.namespace["tool"]("schema test", params)

        @decorate
        def another_tool(maybe=None):
            return maybe

        props = self.namespace["TOOLS"]["another_tool"]["schema"]["function"]["parameters"]["properties"]
        self.assertTrue(props["maybe"]["optional"])


if __name__ == "__main__":
    unittest.main()
