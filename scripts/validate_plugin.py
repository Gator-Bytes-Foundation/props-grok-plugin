#!/usr/bin/env python3
"""Validate Cursor / Grok plugin manifests, paths, and skill frontmatter."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PLUGIN_NAME = "props-grok-plugin"
PROD_MCP_URL = "https://mcp.propsgamify.com/mcp"
TEST_MCP_URL = "https://props-grok-mcp-test.web.app/mcp"
TOOLS_LIST_REL = "scripts/tools_list.json"

CURSOR_FIELDS = {
    "name",
    "description",
    "version",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "logo",
    "skills",
    "mcpServers",
    "variables",
}

PATH_KEYS = {
    "logo",
    "icon",
    "skills",
    "mcpServers",
    "rules",
    "agents",
    "commands",
    "hooks",
}

JSON_FILES = (
    ".cursor-plugin/plugin.json",
    ".grok-plugin/plugin.json",
    "mcp.json",
    ".mcp.json",
)

PENDING_PATHS: set[str] = set()


def tool_names_from_tools_list(payload: object) -> list[str]:
    """Extract sorted unique tool names from a tools-manifest or tools/list payload."""
    tools: object
    if isinstance(payload, list):
        tools = payload
    elif isinstance(payload, dict):
        result = payload.get("result", payload)
        if isinstance(result, dict):
            tools = result.get("tools", [])
        elif isinstance(result, list):
            tools = result
        else:
            tools = []
    else:
        tools = []

    names: set[str] = set()
    if not isinstance(tools, list):
        return []
    for item in tools:
        if isinstance(item, str) and item:
            names.add(item)
        elif isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name:
                names.add(name)
    return sorted(names)


def load_expected_tools(root: Path) -> list[str]:
    """Load tool names from the committed props tools-manifest snapshot."""
    path = root / TOOLS_LIST_REL
    payload = json.loads(path.read_text(encoding="utf-8"))
    names = tool_names_from_tools_list(payload)
    if not names:
        raise ValueError(f"{TOOLS_LIST_REL}: no tool names found")
    return names


def _load_json(root: Path, rel: str, errors: list[str]) -> object | None:
    path = root / rel
    if not path.is_file():
        errors.append(f"missing JSON file: {rel}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{rel}: invalid JSON ({exc})")
        return None


def _is_path_value(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(("http://", "https://")):
        return False
    if value.startswith("{") or value.startswith("$"):
        return False
    return True


def _check_path(root: Path, rel_manifest: str, field: str, value: str, errors: list[str], notes: list[str]) -> None:
    label = f"{rel_manifest} {field}={value!r}"
    if value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value):
        errors.append(f"{label}: absolute paths are not allowed")
        return
    if ".." in Path(value).parts or value.startswith("../") or "/../" in value:
        errors.append(f"{label}: parent-directory segments are not allowed")
        return

    target = (root / value).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: resolves outside the plugin root")
        return

    if value in PENDING_PATHS or value.lstrip("./") in PENDING_PATHS:
        if not target.exists():
            notes.append(f"{label}: pending (file not in repo yet)")
        return

    if not target.exists():
        errors.append(f"{label}: path does not exist")


def _walk_paths(root: Path, rel_manifest: str, data: object, errors: list[str], notes: list[str]) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in PATH_KEYS:
                candidates = value if isinstance(value, list) else [value]
                for item in candidates:
                    if _is_path_value(item):
                        _check_path(root, rel_manifest, key, item, errors, notes)
            else:
                _walk_paths(root, rel_manifest, value, errors, notes)
    elif isinstance(data, list):
        for item in data:
            _walk_paths(root, rel_manifest, item, errors, notes)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str] | None:
    if not text.startswith("---"):
        return None
    match = re.match(r"^---\n(.*?)\n---\n?", text, flags=re.S)
    if not match:
        return None
    fields: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields, text[match.end() :]


def _mcp_url(data: object) -> object:
    if not isinstance(data, dict):
        return None
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return None
    props = servers.get("props")
    if not isinstance(props, dict):
        return None
    return props.get("url")


def _validate_skill(root: Path, path: Path, allowed_tools: set[str], errors: list[str]) -> None:
    rel = path.relative_to(root).as_posix()
    parsed = parse_frontmatter(path.read_text(encoding="utf-8"))
    if parsed is None:
        errors.append(f"{rel}: missing YAML frontmatter delimited by ---")
        return
    fields, body = parsed
    if not fields.get("name"):
        errors.append(f"{rel}: frontmatter is missing name")
    elif not re.fullmatch(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?", fields["name"]):
        errors.append(f"{rel}: name must be kebab-case")
    if not fields.get("description"):
        errors.append(f"{rel}: frontmatter is missing description")

    if re.search(r"(?<![Ee])[Vv]enture\b", body + "\n" + fields.get("description", "")):
        errors.append(f"{rel}: say Eventure, never Venture")

    mentioned = set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", body))
    unknown = sorted(name for name in mentioned if name not in allowed_tools)
    if unknown:
        errors.append(f"{rel}: unknown tool-like names {unknown}")
    missing = sorted(allowed_tools - mentioned)
    if missing:
        errors.append(f"{rel}: does not mention required tools {missing}")


def validate(root: Path) -> list[str]:
    """Return validation errors for a plugin root."""
    errors: list[str] = []
    notes: list[str] = []

    try:
        allowed_tools = set(load_expected_tools(root))
    except FileNotFoundError:
        errors.append(f"missing {TOOLS_LIST_REL} (MCP tools/list source of truth)")
        allowed_tools = set()
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{TOOLS_LIST_REL}: {exc}")
        allowed_tools = set()

    cursor = _load_json(root, ".cursor-plugin/plugin.json", errors)
    grok = _load_json(root, ".grok-plugin/plugin.json", errors)

    if isinstance(cursor, dict):
        extra = sorted(set(cursor) - CURSOR_FIELDS)
        if extra:
            errors.append(f".cursor-plugin/plugin.json: undocumented fields {extra}")
        if cursor.get("name") != PLUGIN_NAME:
            errors.append(f".cursor-plugin/plugin.json: name must be {PLUGIN_NAME}")
        if cursor.get("license") != "Apache-2.0":
            errors.append(".cursor-plugin/plugin.json: license must be Apache-2.0")
        if cursor.get("logo") != "assets/logo.png":
            errors.append(".cursor-plugin/plugin.json: logo must be assets/logo.png")
        author = cursor.get("author")
        if not isinstance(author, dict) or not author.get("name"):
            errors.append(".cursor-plugin/plugin.json: author.name is required")

    if isinstance(grok, dict):
        if grok.get("name") != PLUGIN_NAME:
            errors.append(f".grok-plugin/plugin.json: name must be {PLUGIN_NAME}")
        if grok.get("icon") != "assets/logo.png":
            errors.append(".grok-plugin/plugin.json: icon must be assets/logo.png")

    if (
        isinstance(cursor, dict)
        and isinstance(grok, dict)
        and cursor.get("name") != grok.get("name")
    ):
        errors.append(
            f"manifest names differ: .cursor-plugin={cursor.get('name')!r} "
            f".grok-plugin={grok.get('name')!r} (both must be {PLUGIN_NAME})"
        )

    mcp = _load_json(root, "mcp.json", errors)
    if isinstance(mcp, dict) and _mcp_url(mcp) != PROD_MCP_URL:
        errors.append(f"mcp.json: props.url must be {PROD_MCP_URL}")

    grok_mcp = _load_json(root, ".mcp.json", errors)
    if isinstance(grok_mcp, dict) and _mcp_url(grok_mcp) != PROD_MCP_URL:
        errors.append(f".mcp.json: props.url must be {PROD_MCP_URL}")

    test_mcp_path = root / "mcp.test.json"
    if test_mcp_path.is_file():
        test_mcp = _load_json(root, "mcp.test.json", errors)
        if isinstance(test_mcp, dict) and _mcp_url(test_mcp) != TEST_MCP_URL:
            errors.append(f"mcp.test.json: props.url must be {TEST_MCP_URL}")

    for rel in JSON_FILES:
        data = _load_json(root, rel, errors)
        if data is not None:
            _walk_paths(root, rel, data, errors, notes)

    skills = list((root / "skills").glob("*/SKILL.md"))
    if not skills:
        errors.append("no skills/*/SKILL.md files found")
    for skill in skills:
        _validate_skill(root, skill, allowed_tools, errors)

    if not (root / "LICENSE").is_file():
        errors.append("missing LICENSE")

    for note in notes:
        print(f"NOTE: {note}")
    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        return 1
    print("OK: plugin manifests, paths, and skill frontmatter are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
