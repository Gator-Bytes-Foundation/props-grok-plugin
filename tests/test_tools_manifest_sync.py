#!/usr/bin/env python3
"""Failing-first tests: tools_list.json must be an exact props tools-manifest copy."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS_LIST = ROOT / "scripts/tools_list.json"
SYNC_SCRIPT = ROOT / "scripts/sync_tools_list.py"

SERVER_ORDER = [
    "list_my_active_eventures",
    "list_my_created_eventures",
    "list_my_active_quests",
    "list_my_created_side_quests",
    "get_eventure",
    "list_eventure_quests",
    "get_my_eventure_progress",
    "list_eventure_props_earned",
    "get_eventure_leaderboard",
]

PRIVACY_TEXT = (
    "Do not list, suggest, or volunteer private Eventures the user does not own "
    "or participate in. Looking one up by a link or ID the user provides is fine."
)
PRIVACY_TOOLS = (
    "get_eventure",
    "list_eventure_quests",
    "get_my_eventure_progress",
    "list_eventure_props_earned",
    "get_eventure_leaderboard",
)


def load_sync():
    spec = importlib.util.spec_from_file_location("sync_tools_list", SYNC_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_tools_list() -> object:
    return json.loads(TOOLS_LIST.read_text(encoding="utf-8"))


def manifest_tools(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
        return payload["tools"]
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        tools = payload["result"].get("tools")
        if isinstance(tools, list):
            return tools
    raise AssertionError(f"not a tools-manifest / tools/list payload: {type(payload)}")


class ToolsListIsExactManifestTests(unittest.TestCase):
    def test_file_is_not_a_mixed_jsonrpc_envelope(self):
        payload = load_tools_list()
        self.assertIsInstance(payload, dict)
        self.assertNotIn("method", payload)
        self.assertNotIn("jsonrpc", payload)
        self.assertNotIn("id", payload)
        self.assertEqual(list(payload.keys()), ["name", "pluginRepository", "tools"])
        self.assertEqual(payload["name"], "props-mcp")
        self.assertEqual(payload["pluginRepository"], "Gator-Bytes-Foundation/props-grok-plugin")

    def test_tools_preserve_server_order_not_alphabetical(self):
        names = [tool["name"] for tool in manifest_tools(load_tools_list())]
        self.assertEqual(names, SERVER_ORDER)
        self.assertNotEqual(names, sorted(names))

    def test_each_tool_has_name_description_and_input_schema(self):
        tools = manifest_tools(load_tools_list())
        self.assertEqual(len(tools), 9)
        for tool in tools:
            self.assertIsInstance(tool.get("name"), str)
            self.assertIsInstance(tool.get("description"), str)
            self.assertIsInstance(tool.get("inputSchema"), dict)
            self.assertGreater(len(tool["description"]), 0)

    def test_lookup_tools_use_full_private_eventure_guidance(self):
        tools = {tool["name"]: tool["description"] for tool in manifest_tools(load_tools_list())}
        for name in PRIVACY_TOOLS:
            self.assertIn(PRIVACY_TEXT, tools[name], name)
            self.assertNotIn("Do not list private Eventures.", tools[name].replace(PRIVACY_TEXT, ""))

    def test_sync_default_ref_is_props_default_branch(self):
        sync = load_sync()
        self.assertEqual(sync.DEFAULT_REF, "main")

    def test_readme_notes_ci_needs_props_read_token_secret(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PROPS_READ_TOKEN", text)
        self.assertRegex(text, r"(?i)CI.*PROPS_READ_TOKEN|PROPS_READ_TOKEN.*secret")


class SyncScriptTests(unittest.TestCase):
    def test_sync_module_exists(self):
        self.assertTrue(SYNC_SCRIPT.is_file(), "scripts/sync_tools_list.py is required")
        sync = load_sync()
        self.assertTrue(hasattr(sync, "manifests_differ"))
        self.assertTrue(hasattr(sync, "fetch_canonical_manifest"))
        self.assertTrue(hasattr(sync, "check_local_matches_remote"))

    def test_manifests_differ_on_any_field_change(self):
        sync = load_sync()
        local = {
            "tools": [
                {
                    "name": "get_eventure",
                    "description": "short",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
        remote = {
            "tools": [
                {
                    "name": "get_eventure",
                    "description": "full text. Do not list private Eventures.",
                    "inputSchema": {"type": "object", "required": ["eventureId"]},
                }
            ]
        }
        self.assertTrue(sync.manifests_differ(local, remote))
        self.assertFalse(sync.manifests_differ(remote, remote))

    def test_check_fails_when_fetched_manifest_differs(self):
        sync = load_sync()
        remote = {
            "tools": [
                {
                    "name": "list_my_active_eventures",
                    "description": "canonical",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "tools_list.json"
            local_path.write_text(
                json.dumps({"jsonrpc": "2.0", "method": "tools/list", "result": remote}),
                encoding="utf-8",
            )
            with patch.object(sync, "fetch_canonical_manifest", return_value=remote):
                differs, message = sync.check_local_matches_remote(local_path)
            self.assertTrue(differs, message)

    def test_check_passes_when_local_is_exact_copy(self):
        sync = load_sync()
        remote = {
            "tools": [
                {
                    "name": "list_my_active_eventures",
                    "description": "canonical",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "tools_list.json"
            local_path.write_text(json.dumps(remote, indent=2) + "\n", encoding="utf-8")
            with patch.object(sync, "fetch_canonical_manifest", return_value=remote):
                differs, message = sync.check_local_matches_remote(local_path)
            self.assertFalse(differs, message)


if __name__ == "__main__":
    sys.exit(not unittest.main(verbosity=2))
