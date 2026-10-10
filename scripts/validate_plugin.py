#!/usr/bin/env python3
"""Validate Cursor / Grok plugin manifests, paths, and skill frontmatter."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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

ALLOWED_TOOLS = {
    "list_my_active_eventures",
    "list_my_created_eventures",
    "list_my_active_quests",
    "list_my_created_side_quests",
    "get_eventure",
    "list_eventure_quests",
    "get_my_eventure_progress",
    "list_eventure_props_earned",
    "get_eventure_leaderboard",
}

errors: list[str] = []
notes: list[str] = []


def err(message: str) -> None:
    errors.append(message)


def load_json(rel: str) -> object | None:
    path = ROOT / rel
    if not path.is_file():
        err(f"missing JSON file: {rel}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        err(f"{rel}: invalid JSON ({exc})")
        return None


def is_path_value(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(("http://", "https://")):
        return False
    if value.startswith("{") or value.startswith("$"):
        return False
    return True


def check_path(rel_manifest: str, field: str, value: str) -> None:
    label = f"{rel_manifest} {field}={value!r}"
    if value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value):
        err(f"{label}: absolute paths are not allowed")
        return
    if ".." in Path(value).parts or value.startswith("../") or "/../" in value:
        err(f"{label}: parent-directory segments are not allowed")
        return

    target = (ROOT / value).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        err(f"{label}: resolves outside the plugin root")
        return

    if value in PENDING_PATHS or value.lstrip("./") in PENDING_PATHS:
        if not target.exists():
            notes.append(f"{label}: pending (file not in repo yet)")
        return

    if not target.exists():
        err(f"{label}: path does not exist")


def walk_paths(rel_manifest: str, data: object) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in PATH_KEYS:
                candidates = value if isinstance(value, list) else [value]
                for item in candidates:
                    if is_path_value(item):
                        check_path(rel_manifest, key, item)
            else:
                walk_paths(rel_manifest, value)
    elif isinstance(data, list):
        for item in data:
            walk_paths(rel_manifest, item)


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


def validate_skill(path: Path) -> None:
    rel = path.relative_to(ROOT).as_posix()
    parsed = parse_frontmatter(path.read_text(encoding="utf-8"))
    if parsed is None:
        err(f"{rel}: missing YAML frontmatter delimited by ---")
        return
    fields, body = parsed
    if not fields.get("name"):
        err(f"{rel}: frontmatter is missing name")
    elif not re.fullmatch(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?", fields["name"]):
        err(f"{rel}: name must be kebab-case")
    if not fields.get("description"):
        err(f"{rel}: frontmatter is missing description")

    if re.search(r"(?<![Ee])[Vv]enture\b", body + "\n" + fields.get("description", "")):
        err(f"{rel}: say Eventure, never Venture")

    mentioned = set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", body))
    unknown = sorted(name for name in mentioned if name not in ALLOWED_TOOLS)
    if unknown:
        err(f"{rel}: unknown tool-like names {unknown}")
    missing = sorted(ALLOWED_TOOLS - mentioned)
    if missing:
        err(f"{rel}: does not mention required tools {missing}")


def main() -> int:
    cursor = load_json(".cursor-plugin/plugin.json")
    if isinstance(cursor, dict):
        extra = sorted(set(cursor) - CURSOR_FIELDS)
        if extra:
            err(f".cursor-plugin/plugin.json: undocumented fields {extra}")
        if cursor.get("name") != "props-grok-plugin":
            err(".cursor-plugin/plugin.json: name must be props-grok-plugin")
        if cursor.get("license") != "Apache-2.0":
            err(".cursor-plugin/plugin.json: license must be Apache-2.0")
        if cursor.get("logo") != "assets/logo.png":
            err(".cursor-plugin/plugin.json: logo must be assets/logo.png")
        author = cursor.get("author")
        if not isinstance(author, dict) or not author.get("name"):
            err(".cursor-plugin/plugin.json: author.name is required")

    grok = load_json(".grok-plugin/plugin.json")
    if isinstance(grok, dict) and grok.get("icon") != "assets/logo.png":
        err(".grok-plugin/plugin.json: icon must be assets/logo.png")

    mcp = load_json("mcp.json")
    if isinstance(mcp, dict):
        url = (
            mcp.get("mcpServers", {}).get("props", {}).get("url")
            if isinstance(mcp.get("mcpServers"), dict)
            else None
        )
        if url != "https://mcp.propsgamify.com/mcp":
            err("mcp.json: props.url must be https://mcp.propsgamify.com/mcp")

    grok_mcp = load_json(".mcp.json")
    if isinstance(grok_mcp, dict):
        url = (
            grok_mcp.get("mcpServers", {}).get("props", {}).get("url")
            if isinstance(grok_mcp.get("mcpServers"), dict)
            else None
        )
        if url != "https://mcp.propsgamify.com/mcp":
            err(".mcp.json: props.url must be https://mcp.propsgamify.com/mcp")

    for rel in JSON_FILES:
        data = load_json(rel)
        if data is not None:
            walk_paths(rel, data)

    skills = list((ROOT / "skills").glob("*/SKILL.md"))
    if not skills:
        err("no skills/*/SKILL.md files found")
    for skill in skills:
        validate_skill(skill)

    if not (ROOT / "LICENSE").is_file():
        err("missing LICENSE")

    for note in notes:
        print(f"NOTE: {note}")
    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        return 1
    print("OK: plugin manifests, paths, and skill frontmatter are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
