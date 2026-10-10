---
name: props-grok
description: Look up Props Eventures, quest sections, progress, props earned, and leaderboards via the read-only Props MCP. Use when the user talks about Props, Eventures, quests, sections, progress, props earned, or leaderboards.
---

# Props (Gamify Life)

Use this plugin when the user talks about **Props**, **Eventures**, **quests**, **sections** (quest groupings on an Eventure), progress, **props earned**, or leaderboards.

Always say **Eventure** (that exact product noun). In user-facing text say **section** for quest groupings. Legacy code may call a section a `saga` — do not say "saga" to the user.

## Rules

- Prefer **read tools** first (`list_my_active_eventures`, `get_eventure`, `list_eventure_quests`, etc.).
- Say **section** in user-facing text, not "saga".
- Do not list, suggest, or volunteer private Eventures the user does not own or participate in. Looking one up by a link or ID the user provides is fine.
- Do not claim to create or complete quests in v1 (write tools are phase 2 with explicit confirmation).
- If OAuth is missing, tell the user to connect Props when Cursor prompts — sign in with the same Google account they use in Props and grant **`props.read`**.

## Tools (v1, read-only)

Only these nine tools exist. Do not invent others.

| Tool | When to use |
|------|-------------|
| `list_my_active_eventures` | Eventures the signed-in user is actively participating in (dashboard active row). Optional `userDisplayName` is a log label only. |
| `list_my_created_eventures` | Solo Eventures the user created (paginated: `pageSize`, `cursor`). |
| `list_my_active_quests` | Side quests and quest participation for the signed-in user. |
| `list_my_created_side_quests` | Side quests the user created (paginated: `pageSize`, `cursor`). |
| `get_eventure` | Eventure profile bootstrap: permissions, group, author — not the full quest list. Requires `eventureId`. |
| `list_eventure_quests` | Quests on an Eventure (sections). Respects publish/visibility for non-managers. Requires `eventureId`. |
| `get_my_eventure_progress` | Progress counters for one Eventure for the signed-in user. Requires `eventureId`. |
| `list_eventure_props_earned` | Props on an Eventure and whether the user collected them this session. Requires `eventureId`. |
| `get_eventure_leaderboard` | Leaderboard for an Eventure session (points or quests completed). Requires `eventureId`. |

## Typical flows

- "What Eventures am I in?" → `list_my_active_eventures`
- "Which Eventures did I create?" → `list_my_created_eventures`
- "What quests am I on?" → `list_my_active_quests`
- "Which side quests did I create?" → `list_my_created_side_quests`
- "What's this Eventure?" → `get_eventure` with `eventureId`
- "Show quests / sections in this Eventure" → `list_eventure_quests` with `eventureId`
- "How am I doing on X?" → `get_my_eventure_progress`
- "Which props have I earned?" → `list_eventure_props_earned`
- "Leaderboard for X" → `get_eventure_leaderboard`
