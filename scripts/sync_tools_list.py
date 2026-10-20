#!/usr/bin/env python3
"""Fetch the canonical props tools-manifest and sync or check scripts/tools_list.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL = ROOT / "scripts/tools_list.json"
DEFAULT_REPO = "Gator-Bytes-Foundation/props"
DEFAULT_PATH = "firebase/grokbot-connector/tools-manifest.json"
DEFAULT_REF = "main"
USER_AGENT = "props-grok-plugin-tools-sync"


def env_or(name: str, fallback: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or fallback


def auth_token() -> str | None:
    for name in ("PROPS_READ_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def request_headers(token: str | None, raw: bool = True) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if raw:
        headers["Accept"] = "application/vnd.github.raw"
    else:
        headers["Accept"] = "application/vnd.github+json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _read_url(url: str, headers: dict[str, str], opener: Callable[..., object] | None = None) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    open_url = opener or urllib.request.urlopen
    with open_url(request, timeout=30) as response:  # type: ignore[arg-type]
        return response.read()


def fetch_canonical_text(
    *,
    repo: str | None = None,
    path: str | None = None,
    ref: str | None = None,
    token: str | None = None,
    opener: Callable[..., object] | None = None,
) -> str:
    repo = repo or env_or("PROPS_TOOLS_MANIFEST_REPO", DEFAULT_REPO)
    path = path or env_or("PROPS_TOOLS_MANIFEST_PATH", DEFAULT_PATH)
    ref = ref or env_or("PROPS_TOOLS_MANIFEST_REF", DEFAULT_REF)
    token = token if token is not None else auth_token()
    encoded_path = urllib.parse.quote(path)
    encoded_ref = urllib.parse.quote(ref, safe="")
    api_url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={encoded_ref}"
    raw_url = f"https://raw.githubusercontent.com/{repo}/{urllib.parse.quote(ref, safe='/:')}/{path}"
    errors: list[str] = []
    for url, raw in ((api_url, True), (raw_url, True)):
        try:
            body = _read_url(url, request_headers(token, raw=raw), opener=opener)
            text = body.decode("utf-8")
            json.loads(text)
            return text
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError(
        "failed to fetch canonical tools-manifest from the props repo; "
        + " ; ".join(errors)
        + ". Set PROPS_READ_TOKEN (or GH_TOKEN) if the repo is private."
    )


def fetch_canonical_manifest(**kwargs) -> object:
    return json.loads(fetch_canonical_text(**kwargs))


def load_local_manifest(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def manifests_differ(local: object, remote: object) -> bool:
    return local != remote


def check_local_matches_remote(
    local_path: Path,
    *,
    remote: object | None = None,
    **fetch_kwargs,
) -> tuple[bool, str]:
    if not local_path.is_file():
        return True, f"missing {local_path}"
    local = load_local_manifest(local_path)
    if remote is None:
        remote = fetch_canonical_manifest(**fetch_kwargs)
    if manifests_differ(local, remote):
        return True, (
            f"{local_path} differs from the props tools-manifest "
            f"(repo={env_or('PROPS_TOOLS_MANIFEST_REPO', DEFAULT_REPO)} "
            f"path={env_or('PROPS_TOOLS_MANIFEST_PATH', DEFAULT_PATH)} "
            f"ref={env_or('PROPS_TOOLS_MANIFEST_REF', DEFAULT_REF)})"
        )
    return False, f"{local_path} matches the props tools-manifest"


def write_local_manifest(local_path: Path, **fetch_kwargs) -> None:
    text = fetch_canonical_text(**fetch_kwargs)
    if not text.endswith("\n"):
        text += "\n"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="fail if local tools_list.json differs")
    group.add_argument("--write", action="store_true", help="overwrite local tools_list.json from the props repo")
    parser.add_argument("--repo", default=None, help=f"GitHub repo (default {DEFAULT_REPO})")
    parser.add_argument("--path", default=None, help=f"path in that repo (default {DEFAULT_PATH})")
    parser.add_argument("--ref", default=None, help="git ref (default $PROPS_TOOLS_MANIFEST_REF or the props default branch, main)")
    parser.add_argument("--local", default=str(DEFAULT_LOCAL), help="local snapshot path")
    args = parser.parse_args(argv)

    fetch_kwargs = {"repo": args.repo, "path": args.path, "ref": args.ref}
    local_path = Path(args.local)
    try:
        if args.write:
            write_local_manifest(local_path, **fetch_kwargs)
            print(f"wrote {local_path} from the props tools-manifest")
            return 0
        differs, message = check_local_matches_remote(local_path, **fetch_kwargs)
        print(message)
        return 1 if differs else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
