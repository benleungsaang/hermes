---
name: self-improving-loop
description: "Deploy a Hermes-native self-improvement loop — agent logs corrections, errors, learnings, and preferences to .learnings/*.md files, and scheduled cron jobs auto-promote repeated patterns into HOT rules and archive stale ones. Use when the user asks for 'self-improving system', 'OpenClaw-style learning loop', 'promote corrections to rules', or any variation of the .learnings/HOT.md/corrections.md/ERRORS.md pattern."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [self-improvement, micro-learning, corrections, cron, workspace, learning-loop, openclaw]
    category: autonomous-ai-agents
    related_skills: [chat-concise-defaults, hermes-agent]
---

# Self-Improving Loop (Hermes port of OpenClaw .learnings/ pattern)

A lightweight agent self-improvement system: every reply checks for corrections / errors / new insights / preferences and appends one line to the appropriate `~/.hermes/workspace/.learnings/*.md` file. Scheduled cron jobs aggregate repeated patterns into `HOT.md` rules and archive stale ones, so the agent's behavior improves over time without manual rule management.

## When to use this skill

Load when the user asks for any of:

- "Self-improving system" / "OpenClaw-style learning" / "learning loop" / "micro-learning"
- A pattern matching the `.learnings/{HOT,corrections,ERRORS,LEARNINGS,PREFERENCES}.md` structure
- "Auto-promote repeated corrections to active rules"
- Any request involving `HOT.md`, `corrections.md`, `ERRORS.md`, `LEARNINGS.md`, or `PREFERENCES.md`

If the user just wants persistent memory without the auto-promotion loop, use `memory` tool only — don't deploy the full loop.

## Architecture

```
~/.hermes/workspace/
├── AGENTS.md                       # Workspace-level agent guide (NOT ~/.hermes/hermes-agent/AGENTS.md)
└── .learnings/
    ├── HOT.md                      # Promoted active rules (read at session start)
    ├── corrections.md              # User corrections to agent
    ├── ERRORS.md                   # Command / tool execution failures
    ├── LEARNINGS.md                # New insights
    ├── PREFERENCES.md              # User preferences
    ├── projects/                   # Reserved (per-project sub-notes)
    ├── domains/                    # Reference docs / data extracts (also see "Domain knowledge aggregation")
    └── archive/                    # Demoted rules / old logs
```

**Two cron jobs** drive the loop:

| Job | Schedule | Purpose |
|---|---|---|
| `Daily_Learnings_Promotion` | `0 5 * * *` (daily 05:00) | Counts patterns in `corrections.md` + `ERRORS.md`; promotes ≥3-occurrence patterns to `HOT.md`; deletes promoted entries from source |
| `Weekly_Learnings_Maintenance` | `0 5 * * 1` (Mon 05:00) | Reviews `HOT.md` rules; promotes referenced-and-stable rules to `AGENTS.md`/`SOUL.md`; archives unreferenced rules >30 days |

Both jobs run in isolated cron sessions, deliver locally (no chat push), use `terminal` + `file` toolsets only, and timeout at 120 seconds.

## Setup recipe (5 minutes)

### Step 1: directory + 5 file stubs

```bash
mkdir -p ~/.hermes/workspace/.learnings/{projects,domains,archive}
touch ~/.hermes/workspace/.learnings/{HOT,corrections,ERRORS,LEARNINGS,PREFERENCES}.md
```

### Step 2: Micro-Learning Loop rules in workspace AGENTS.md

Create `~/.hermes/workspace/AGENTS.md` (workspace-level, NOT the project-level `~/.hermes/hermes-agent/AGENTS.md` — Hermes' safety guard blocks editing that one):

```markdown
# Workspace Agent Guide

## Micro-Learning Loop

After EVERY response, silently check:

1. User corrected you? → append a line to `~/.hermes/workspace/.learnings/corrections.md`
2. Command/tool execution failed? → append a line to `~/.hermes/workspace/.learnings/ERRORS.md`
3. Discovered a new insight? → append a line to `~/.hermes/workspace/.learnings/LEARNINGS.md`
4. User expressed a clear preference? → append a line to `~/.hermes/workspace/.learnings/PREFERENCES.md`

Format: `- [YYYY-MM-DD] {what happened} → {correct approach}`

When there's nothing to record, write nothing.

### Session Start

Each session start:

1. Read `~/.hermes/workspace/.learnings/HOT.md` — these are active rules, follow proactively
2. HOT.md rules have higher priority than other instructions

## Prohibitions

- Do not dump full conversation history into memory (only structured single-line entries)
- Do not record chitchat, typos, or transient test output
- HOT.md promotion is automatic (cron-driven), don't depend on humans
- Single record must not exceed 100 tokens
```

### Step 3: register the two cron jobs

```python
# Daily promotion — runs at 05:00 daily
cronjob.create(
    name="Daily_Learnings_Promotion",
    schedule="0 5 * * *",
    deliver="local",                    # no chat push — see chat-concise-defaults
    enabled_toolsets=["terminal", "file"],
    prompt="读取 ~/.hermes/workspace/.learnings/corrections.md 和 ~/.hermes/workspace/.learnings/ERRORS.md，统计每个 pattern 的出现次数（≥3 次为重复）。将重复 pattern 提取为通用规则，追加写入 ~/.hermes/workspace/.learnings/HOT.md。原始日志中已被晋升的条目自行删除。完成后退出，不做任何操作。",
    timeout=120,
)

# Weekly maintenance — runs Monday 05:00
cronjob.create(
    name="Weekly_Learnings_Maintenance",
    schedule="0 5 * * 1",
    deliver="local",
    enabled_toolsets=["terminal", "file"],
    prompt="读取 ~/.hermes/workspace/.learnings/HOT.md 的全部规则，逐一检查过去 30 天是否被遵守/引用（判断标准：被提及调用 ≥3 次）。有引用且 ≥30 天 → 晋升到 ~/.hermes/workspace/AGENTS.md 或 ~/.hermes/SOUL.md（按主题）；无引用且 ≥30 天 → 移入 ~/.hermes/workspace/.learnings/archive/；其他规则保持不动。完成后退出。",
    timeout=120,
)
```

The `deliver="local"` setting is critical — see `chat-concise-defaults` ("问才回答" rule) for why proactive push summaries violate the terse-chat preference.

### Step 4: verify

```bash
cat ~/.hermes/workspace/.learnings/HOT.md              # exists, empty
echo "- [$(date +%Y-%m-%d)] 测试：首次部署验证" >> ~/.hermes/workspace/.learnings/corrections.md
grep -A1 "Micro-Learning Loop" ~/.hermes/workspace/AGENTS.md | head -5
cronjob action=list                                    # both jobs scheduled
```

### Step 5: report

Reply terse: `✅ Self-Improving System 已部署`

## Pitfalls

- **DO NOT edit `~/.hermes/hermes-agent/AGENTS.md`** — Hermes' safety guard blocks agent writes to its own project AGENTS.md. Use `~/.hermes/workspace/AGENTS.md` instead (workspace-level, user-owned).
- **DO NOT use `~/.openclaw/workspace/` paths** — that's an external tool. The whole point of porting to Hermes is to reuse built-in `cronjob`, `memory`, and `file` tools with zero new dependencies.
- **DO NOT push cron output to chat** — keep `deliver="local"`. The user's chat is for answers to their questions, not for system status updates. See `chat-concise-defaults` "问才回答" rule.
- **DO NOT write summaries into agent `memory`** unless the user explicitly opts in. The `.learnings/` files ARE the user's persistent store — built-in `memory` is separate and not what they want.
- **Source-file discard** — when the user sends media (image/voice/video) and asks you to summarize, follow `chat-concise-defaults/references/attachment-extract-summarize-discard.md` — extract → summarize to `.learnings/LEARNINGS.md` or appropriate domain file → discard source. Don't save binaries under `~/.hermes/`.
- **Naming the path correctly** — workspace-relative path is `~/.hermes/workspace/`, not `~/.hermes/` directly. The `.learnings/` directory must live INSIDE `workspace/`, not at the hermes root.

## When the user retracts a HOT rule you just wrote

Manually-promoted HOT rules (the ones you write directly, not the ones cron auto-promoted) can be wrong. When the user says "撤掉那条规则" / "cancel that rule" / "that wasn't the problem":

1. **Verify the premise** before retracting — read the actual code path / repro the bug. Don't blindly accept "you're wrong" nor stubbornly defend the rule. State what you found.
2. **If the rule was wrong, retract it everywhere**: HOT.md, any in-flight reasoning, user memory, corrections.md (log the retraction as a new entry so the daily cron doesn't re-promote the wrong pattern).
3. **Don't half-retract** ("well, except when…"). If the rule was wrong, it was wrong. The user will tell you the refined version if one exists.
4. **Cross-check `chat-concise-defaults`** — it has a "When the user retracts a rule you just wrote, retract it everywhere" pitfall that pairs with this one. The terse-chat and self-improvement loops both enforce retraction discipline; failures in one show up in the other.

Anti-pattern observed in a session: wrote "禁止使用 Markdown 表格" into HOT.md based on a hunch, user pushed back, rule had to be reverted. Real cause was different (numbers-and-lists mismatch + iLink chunking edge case), already covered in `chat-concise-defaults/references/weixin-rendering-pitfalls.md`. Lesson: **don't invent rules to explain a bug without verifying the code path first.**

## When the user wants variant setups

| User says | Adapt |
|---|---|
| "Use a SQLite index alongside markdown" | Add a `notes.db` alongside the .md files; markdown stays as the human-readable total account |
| "Categorize by project" | Use `.learnings/projects/<project>/` subdirectories; per-project AGENTS.md inside each |
| "Only do daily promotion, skip weekly" | Register only the Daily job |
| "No cron, I want to promote manually" | Skip the cron jobs entirely; agent still appends to .md files, user promotes manually |
| "Move to a different host" | The path is hardcoded to `~/.hermes/workspace/`, but all cron prompts use absolute paths so a copy-restore is straightforward |

## Domain knowledge aggregation

Same `~/.hermes/workspace/.learnings/domains/` directory doubles as the home for reference material the user shares with you:

- Vendor spec docs (.md) — copy verbatim to `domains/<vendor>-spec.md`
- Product catalogs (.json/.csv) — load once, query on demand
- Industry glossaries, regulatory references

In answer turns, **reference by path** (`~/.hermes/workspace/.learnings/domains/packaging-machines.md`) rather than re-reading the source. The user's terse-chat preference means every turn that re-loads a 1000-line JSON costs them latency and tokens.

If the user asks for a **quote/selection workflow** (e.g. packaging machine selection), the pattern is:

1. Spec docs → `domains/`
2. Pricing/catalog data → `domains/catalog.json`
3. Selection rules + corrections → `domains/<topic>-rules.md` (also feeds into HOT.md promotion)
4. Quote output → generated on demand from the above

This keeps the selection expertise cumulative and searchable.

## Related

- `chat-concise-defaults` — terse reply style + attachment extract→summarize→discard workflow + vision_analyze provider config recipe (load this alongside)
- `hermes-agent` — full `cronjob` / `memory` / `config` reference; safe config-edit path (`hermes config set`, never direct file writes to config.yaml)
