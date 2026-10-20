# Props plugin for Cursor

Official **Props (Gamify Life)** plugin: skills plus MCP config for the Props gamified community app. Ask Cursor about your Eventures, quest sections, progress, props earned, and leaderboards.

v1 is **read-only**. The plugin talks to the hosted Props MCP server — no API keys and no plugin variables.

This repo also keeps a [Grok Build](https://github.com/xai-org/plugin-marketplace) manifest under `.grok-plugin/` that points at the same production MCP URL.

## Install

After Props is listed on the Cursor Marketplace, install **props-grok-plugin** from Marketplace / Customize.

### Local test (before Marketplace listing)

Copy this repo into Cursor's local plugins directory, then restart Cursor:

```bash
git clone https://github.com/Gator-Bytes-Foundation/props-grok-plugin.git ~/.cursor/plugins/local/props-grok-plugin
```

Or, from a checkout:

```bash
cp -R . ~/.cursor/plugins/local/props-grok-plugin
```

Enable the local plugin in Cursor settings if it does not appear automatically.

## Sign-in

1. Open a chat and use Props (or connect the **props** MCP server when Cursor prompts).
2. Cursor starts browser OAuth 2.1 (dynamic client registration + PKCE).
3. Sign in with the **same Google account** you use in Props.
4. Grant the **`props.read`** scope.

No API keys. Tokens stay in Cursor's MCP auth store.

## MCP server

Production Streamable HTTP (this is what `mcp.json` and `.mcp.json` ship):

`https://mcp.propsgamify.com/mcp`

### Test build

To point a local checkout at the hosted test MCP instead of production, use:

`https://props-grok-mcp-test.web.app/mcp`

A ready-made config is in `mcp.test.json`. Copy it over `mcp.json` and set the same `url` in `.mcp.json` in your local checkout only — do not commit that swap. OAuth for the test MCP is discovered automatically from `https://props-grok-oauth-test.web.app`.

## Tools (v1, read-only)

| Tool | What it returns |
|------|-----------------|
| `list_my_active_eventures` | Eventures you are actively participating in |
| `list_my_created_eventures` | Solo Eventures you created |
| `list_my_active_quests` | Side quests and quest participation |
| `list_my_created_side_quests` | Side quests you created |
| `get_eventure` | Eventure profile bootstrap (permissions, group, author — not the full quest list) |
| `list_eventure_quests` | Quests on an Eventure (sections) |
| `get_my_eventure_progress` | Your progress counters for one Eventure |
| `list_eventure_props_earned` | Props on an Eventure and whether you collected them this session |
| `get_eventure_leaderboard` | Leaderboard for an Eventure session (points or quests completed) |

User-facing copy uses **section** for quest groupings on an Eventure (legacy code may say `saga`). The product name is **Eventure**, never "Venture".

If a lookup is not visible, say the Eventure is private or does not exist. Do not list, suggest, or volunteer other people's private Eventures. Looking one up by a link or ID the user provides is fine.

Write tools (create or complete quests) are not in v1. v1 advertises the **`props.read`** scope only.

## Privacy and terms

The plugin does **not** keep all traffic under `propsgamify.com`. Hosts it uses:

| Host | Role |
|------|------|
| `mcp.propsgamify.com` | Production MCP |
| `props-grok-mcp-test.web.app` | Test-build MCP |
| `props-grok-oauth-test.web.app` | Props OAuth authorization server (not under `propsgamify.com`) |
| `accounts.google.com` | Google sign-in (required during the browser OAuth flow) |

See [props.marketing](https://props.marketing) for privacy and terms.

## Validate locally

```bash
python3 scripts/validate_plugin.py
python3 -m unittest discover -s tests -v
```

`scripts/tools_list.json` is an exact copy of the canonical `firebase/grokbot-connector/tools-manifest.json` in [Gator-Bytes-Foundation/props](https://github.com/Gator-Bytes-Foundation/props) (same order, names, descriptions, and schemas). Refresh it from the props default branch (`main`), or set `PROPS_TOOLS_MANIFEST_REF` to another ref:

```bash
python3 scripts/sync_tools_list.py --write
python3 scripts/sync_tools_list.py --check
```

CI runs `--check` and fails if the snapshot differs. That job needs the **`PROPS_READ_TOKEN` repository secret** (a GitHub token that can read the private props repo). Optionally override the ref with the `PROPS_TOOLS_MANIFEST_REF` repository variable.

## License

Apache-2.0 — Copyright 2026 Gator Bytes Co. See [LICENSE](LICENSE).
