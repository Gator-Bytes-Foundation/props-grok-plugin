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

Production Streamable HTTP:

`https://mcp.propsgamify.com/mcp`

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

Do not list, suggest, or volunteer private Eventures the user does not own or participate in. Looking one up by a link or ID the user provides is fine.

Write tools (create or complete quests) are not in v1. v1 advertises the **`props.read`** scope only.

## Privacy and terms

Network calls go only to Props MCP and OAuth endpoints under `propsgamify.com`. See [props.marketing](https://props.marketing) for privacy and terms.

## Validate locally

```bash
python3 scripts/validate_plugin.py
```

## License

Apache-2.0 — Copyright 2026 Gator Bytes Co. See [LICENSE](LICENSE).
