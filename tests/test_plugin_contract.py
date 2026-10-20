#!/usr/bin/env python3
"""Contract tests for manifests, the tools/list source of truth, and skill wording."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "props-grok-plugin"
PROD_MCP_URL = "https://mcp.propsgamify.com/mcp"
TEST_MCP_URL = "https://props-grok-mcp-test.web.app/mcp"
PROD_MCP_HOST = "mcp.propsgamify.com"
TEST_MCP_HOST = "props-grok-mcp-test.web.app"
OAUTH_HOST = "props-grok-oauth-test.web.app"
GOOGLE_HOST = "accounts.google.com"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_plugin", ROOT / "scripts" / "validate_plugin.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ManifestNameTests(unittest.TestCase):
    def test_cursor_and_grok_plugin_names_match(self):
        cursor = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text(encoding="utf-8"))
        grok = json.loads((ROOT / ".grok-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(cursor["name"], PLUGIN_NAME)
        self.assertEqual(grok["name"], PLUGIN_NAME)
        self.assertEqual(cursor["name"], grok["name"])


class ToolsListSourceOfTruthTests(unittest.TestCase):
    def test_committed_tools_list_is_valid_mcp_payload(self):
        path = ROOT / "scripts/tools_list.json"
        self.assertTrue(
            path.is_file(),
            "scripts/tools_list.json must be the committed MCP tools/list source of truth",
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        vp = load_validator()
        names = vp.tool_names_from_tools_list(payload)
        self.assertGreaterEqual(len(names), 1)
        self.assertEqual(names, sorted(set(names)))
        self.assertIn("get_eventure", names)
        self.assertIn("list_my_active_eventures", names)

    def test_validator_loads_expected_tools_from_tools_list(self):
        vp = load_validator()
        expected = vp.load_expected_tools(ROOT)
        snapshot = vp.tool_names_from_tools_list(
            json.loads((ROOT / "scripts/tools_list.json").read_text(encoding="utf-8"))
        )
        self.assertEqual(expected, snapshot)

    def test_skill_mentions_every_tools_list_name(self):
        vp = load_validator()
        expected = set(vp.load_expected_tools(ROOT))
        skill = (ROOT / "skills/props-grok/SKILL.md").read_text(encoding="utf-8")
        missing = sorted(name for name in expected if name not in skill)
        self.assertEqual(missing, [])

    def test_validator_flags_skill_missing_a_tools_list_name(self):
        vp = load_validator()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "list_my_active_eventures", "description": "x"},
                    {"name": "brand_new_server_tool", "description": "y"},
                ]
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts/tools_list.json").write_text(json.dumps(payload), encoding="utf-8")
            names = vp.tool_names_from_tools_list(payload)
            self.assertIn("brand_new_server_tool", names)
            mentioned = {"list_my_active_eventures"}
            missing = sorted(set(names) - mentioned)
            self.assertEqual(missing, ["brand_new_server_tool"])


class PrivacyAndSkillWordingTests(unittest.TestCase):
    def test_readme_keeps_prod_mcp_url(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(PROD_MCP_URL, text)
        mcp = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(mcp["mcpServers"]["props"]["url"], PROD_MCP_URL)

    def test_readme_documents_test_build_url(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(TEST_MCP_URL, text)
        self.assertTrue(
            (ROOT / "mcp.test.json").is_file(),
            "mcp.test.json should be the documented test-build MCP config",
        )
        test_mcp = json.loads((ROOT / "mcp.test.json").read_text(encoding="utf-8"))
        self.assertEqual(test_mcp["mcpServers"]["props"]["url"], TEST_MCP_URL)

    def test_readme_privacy_names_actual_hosts(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for host in (PROD_MCP_HOST, TEST_MCP_HOST, OAUTH_HOST, GOOGLE_HOST):
            self.assertIn(host, text, f"README privacy section should name {host}")
        self.assertNotIn(
            "Network calls go only to Props MCP and OAuth endpoints under `propsgamify.com`",
            text,
            "Do not claim every host is under propsgamify.com",
        )

    def test_skill_says_private_or_does_not_exist(self):
        text = (ROOT / "skills/props-grok/SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("private or does not exist", text)
        self.assertIn("do not list", text)

    def test_skill_says_google_sign_in_is_required(self):
        text = (ROOT / "skills/props-grok/SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("google sign-in is required", text)


class ValidatorNameAlignmentTests(unittest.TestCase):
    def test_validator_rejects_mismatched_manifest_names(self):
        vp = load_validator()
        cursor = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text(encoding="utf-8"))
        grok = json.loads((ROOT / ".grok-plugin/plugin.json").read_text(encoding="utf-8"))
        grok["name"] = "props"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".cursor-plugin").mkdir()
            (root / ".grok-plugin").mkdir()
            (root / "scripts").mkdir()
            (root / "skills/demo").mkdir(parents=True)
            (root / "assets").mkdir()
            (root / "assets/logo.png").write_bytes(b"x")
            (root / "LICENSE").write_text("license", encoding="utf-8")
            (root / ".cursor-plugin/plugin.json").write_text(json.dumps(cursor), encoding="utf-8")
            (root / ".grok-plugin/plugin.json").write_text(json.dumps(grok), encoding="utf-8")
            (root / "mcp.json").write_text(
                json.dumps({"mcpServers": {"props": {"url": PROD_MCP_URL}}}),
                encoding="utf-8",
            )
            (root / ".mcp.json").write_text(
                json.dumps({"mcpServers": {"props": {"url": PROD_MCP_URL}}}),
                encoding="utf-8",
            )
            (root / "scripts/tools_list.json").write_text(
                json.dumps({"result": {"tools": [{"name": "list_my_active_eventures"}]}}),
                encoding="utf-8",
            )
            (root / "skills/demo/SKILL.md").write_text(
                "---\nname: demo\ndescription: Demo skill.\n---\n\nUse `list_my_active_eventures`.\n",
                encoding="utf-8",
            )
            errors = vp.validate(root)
            self.assertTrue(
                any("name" in message and "props-grok-plugin" in message for message in errors),
                errors,
            )


if __name__ == "__main__":
    sys.exit(not unittest.main(verbosity=2))
