---
name: hermes-personal-knowledge-loop
description: "Use Hermes as a personal knowledge + reminders + cross-session memory assistant for a non-technical or semi-technical user on WeChat. Covers the local-first storage layout (notes/ + .learnings/ + cron promotion), the extract→summarize→discard source-file policy, the FTS5+Markdown dual storage for retrieval, and the ask-on-demand (no proactive push) reply pattern. Load when the user asks for a memory helper / reminders / 'remember this for me' / 'what did I tell you about X' workflows."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memory, notes, reminders, personal-assistant, knowledge-base, cron, qmd, chinese]
    category: productivity
---

# Hermes Personal Knowledge Loop

Run Hermes as a quiet personal assistant that records what you tell it (text/voice/image/video), indexes it for fast recall, and only speaks up when asked. Designed for a WeChat / chat-platform user who wants memory without noise.

## When to use this skill

Load when the user asks for any of:

- "帮我记录 / 提醒 / 记住这件事" (record a reminder / remember this)
- "我之前提过的 X 是什么" (what was the X I mentioned before?)
- "几月几日我提过 Y" (when did I mention Y?)
- "归类整理" / "笔记助手" / "个人事项"
- Mentions of `~/.hermes/workspace/notes/` or `~/.hermes/workspace/.learnings/`
- Wants a long-running companion that learns their preferences across sessions

NOT for: project memory of a codebase (use `codebase-inspection`), task list management (use `todo`), or scheduled cron jobs unrelated to personal notes (use `cronjob` directly).

## Storage layout

Three directories, each with a distinct role. Don't mix them.

```
~/.hermes/workspace/
├── notes/                  # 用户事项 / 待办 / 客户 / 笔记
│   ├── reminders.md        # 待办提醒 (B 主动问时调取)
│   └── <topic>.md          # 主题笔记 (e.g. clients.md, prices.md)
│
└── .learnings/             # Agent 自学习 + 领域知识
    ├── HOT.md              # 最高优先级规则 (session start 读取)
    ├── corrections.md      # 用户纠正记录
    ├── ERRORS.md           # 命令/工具执行失败记录
    ├── LEARNINGS.md        # 新洞见
    ├── PREFERENCES.md      # 用户偏好
    ├── domains/            # 领域知识 (e.g. packaging-machines.md)
    ├── projects/           # 项目笔记
    └── archive/            # 已晋升但不再活跃的规则
```

**Three rules** keep this clean:

1. **HOT.md = highest priority**, read at session start. Only rules that govern behavior across all sessions belong here.
2. **corrections.md / LEARNINGS.md / etc.** are append-only log files. Don't edit past entries — date-stamp new ones.
3. **domains/** is for stable domain knowledge that took multiple sessions to build (e.g. an entire packaging-machine model catalog after months of training). One file per domain.

## The two-track reminders rule

`notes/reminders.md` mixes two unrelated categories the user
explicitly wants kept apart: things the user has to do themselves
(sales work, customer follow-up) vs things to discuss with Hermes
(CAD tooling, memory design). Different lifecycles, different
stakeholders, different statuses — never share a numbering sequence.

**Layout (apply when adding or reorganising entries):**

```
## 🔴 B-工作：B 本人要做的工作待办

### W-001 [YYYY-MM-DD] <一句话标题>
详情、状态、关联

### W-002 ...

## 🔵 B×H-讨论：需要和 Hermes 一起讨论/研究的事项

### D-001 [YYYY-MM-DD] <一句话标题>
详情、状态、待 B 提供的信息

### D-002 ...
```

**Rules:**

1. **Two independent ID sequences.** 🔴 uses `W-NNN` (Work).
   🔵 uses `D-NNN` (Discussion). Never share a counter.
2. **Prefix every entry with its tag** (`🔴 【B-工作】` or
   `🔵 【B×H-讨论】`) — not just in the section header but inline so
   the entry can be lifted out of context and still self-identify.
3. **Reply gating by question phrasing:**
   - "我还有什么工作" / "工作待办" / **"待办"** (alone) → return only 🔴
   - "我们要讨论什么" / "讨论项" / **"待办项目"** / "待处理项目" → return only 🔵
   - "提醒事项" / "今天要做什么" → return both, but with tags
   - The plain word "待办" = work, "待办项目"/"待处理项目" = discussion. Don't conflate them. (B 明确：2026-06-17 "待办事项一般是指工作待办事项，待处理项目才是BXH")
4. **B-工作 entries track status** (⏳ / ✅ / ❌ / 取消) because the
   user returns to them across sessions. B×H-讨论 entries track
   "待 B 提供信息" / "讨论中" / "已定稿" — different lifecycle.
5. **Mirror this rule into `AGENTS.md`** under a "Reminders 分类规则"
   heading so every session start picks it up automatically, not just
   when this skill is loaded.

**User never queries by ID** (added 2026-06-17 from explicit user
feedback: "我不会使用 W-XXX或者 D-XXX这样的编号问你，这个只是你的内部编号"):

- The agent assigns `W-NNN` / `D-NNN` internally for de-dup, cross-session tracking, and indexing.
- The user always queries with **natural language** ("我之前提过的泰国客户", "配件价格我补了几个", "我们之前说要讨论什么").
- Do NOT ask the user for an ID when answering a recall question. Translate their natural-language query into a `qmd search` / `grep` lookup, not into "which entry are you referring to?".
- Surface the matched entries with tags + short titles + status, not "W-001 says…". The ID is meta — never the user-facing handle.

**File format vs reply format — these are NOT the same** (added 2026-06-17 from explicit user feedback "不要再使用 W-001 或 D-001 编号，就 1. XXX 可以了，每项工作间加些空行分隔方便阅读"):

- The file `notes/reminders.md` uses `### W-001` / `### D-001` headings internally. This is the system's bookkeeping — it does not change.
- The **agent's reply** when the user asks "告诉我待办" / "待办项目" / "今天要做什么" must be a plain numbered list: `1. 标题\n\n2. 标题\n\n3. 标题`. Blank line between each item. No `W-001` prefix, no `🔴` emoji, no `### ` heading in the chat reply.
- This split keeps the file machine-grep-able while the chat reply stays scannable. The agent bridges them at the rendering layer, not the storage layer.

**Lean-by-default for the user's own query tool** (added 2026-06-17):
The user's mental model for "memory helper" is "fast fuzzy recall",
not "structured query engine". When proposing any tool / schema /
cron setup for their personal notes:

- Default to "do nothing" until 10+ entries prove a pattern.
- Do not propose a SQLite / Postgres / vector DB unless they ask.
- Do not propose a cron job unless they ask "每天提醒我".
- Do not propose a 4-tier classification scheme (project / topic / phase / status) — `notes/<topic>.md` flat files are enough until proven otherwise.
- When they say "先做简单功能" / "能快就行" / "不需要复杂架构", that means **stop, ship the minimum, ask if they need more later**. It does not mean "implement a minimum viable subset of the larger design."

**Anti-pattern that motivated this rule:** the agent once mixed its
own engineering progress (qmd installed, bug fixed, HF mirror set)
into the user's work to-do list. The user correctly called this out
as nonsense — those are agent maintenance tasks, not user work.
Engineering/maintenance progress for the agent belongs in
`~/.hermes/workspace/.learnings/MAINTENANCE.md` if the user ever wants
to see it; default is NOT to track it at all.

## The extract→summarize→discard rule

When the user sends media (image / voice / video / document):

1. **Extract**: use the appropriate tool (`vision_analyze` for images, `text_to_speech` reversal isn't reliable — instead use the platform's transcript if available, or ask the user to re-send as text). For documents, use `read_file` or `ocr-and-documents` skill.
2. **Summarize**: produce a short structured text version (date + topic + 1-line per item).
3. **Discard**: do NOT save the source file. The user explicitly said so. Don't even write it to `/tmp`.

The user's rule: "发送给你的文件可以以文字方式归纳不保存源文件."

This applies even to seemingly useful media — the source is gone after summarization, only the structured text persists.

## Indexing for retrieval

Don't store plain Markdown and call it done. Two-tier:

| Tier | Purpose | Tool |
|---|---|---|
| **Source of truth** | Human-readable, the user can edit by hand | `~/.hermes/workspace/notes/<topic>.md` + `.learnings/domains/*.md` |
| **Search index** | Fast recall, semantically aware | `qmd` skill (`official/research/qmd`) |

Workflow:

1. After writing the source-of-truth Markdown file, register its directory with `qmd add <dir>`.
2. The user asks "what did I tell you about X." You run `qmd search "<X>"` and read the top hits.
3. qmd uses BM25 + vector + LLM rerank, so natural-language queries work better than grep.

Don't pre-build a SQLite FTS5 index unless qmd isn't enough. qmd handles Chinese well out of the box.

## The ask-on-demand (no proactive push) pattern

This is the single most important user preference for this workflow:

> "问我时再调取，不推送"

Concretely:

- **Never auto-summarize at session start.** Don't dump "here's what I remember about you." Wait for the user's question.
- **Cron jobs default to `deliver=local`** (not push). They update the local store but don't send a message.
- **Daily / weekly summaries are off by default.** Only enable when the user explicitly asks "每天给我发一下".
- **When a tool output is long**, give a 1-line summary and offer "details?" Don't auto-dump.

## Cron pattern for self-curation

A useful setup (and one the user has already deployed):

```
# Daily 05:00 — promote repeated corrections to HOT.md
"读取 .learnings/corrections.md 和 ERRORS.md，统计每个 pattern 的出现次数（≥3 次为重复）。
将重复 pattern 提取为通用规则，追加写入 .learnings/HOT.md。
原始日志中已被晋升的条目自行删除。"

# Weekly Monday 05:00 — promote cited HOT.md rules to AGENTS.md; archive stale ones
"读取 .learnings/HOT.md 的全部规则，逐一检查过去 30 天是否被遵守/引用。
有引用且 ≥30 天 → 晋升到 AGENTS.md 或 SOUL.md；
无引用且 ≥30 天 → 移入 archive/；其他规则保持不动。"
```

These run in `cronjob` with `deliver=local` and `enabled_toolsets=["terminal", "file"]`.

## Pitfalls

- **Don't write personal facts into the agent's built-in memory.** The user said "具体事项不写入内置记忆; 用户主动问时才检索." Use the local notes/ directory instead.
- **Don't summarize on session start.** Wait for a question. Proactive dumps erode trust ("why are you listing my things back to me?").
- **Don't save source media.** Per user rule. Summarize and discard.
- **Don't pre-build a complex schema.** Start with one `notes/reminders.md` and grow. Schema design can wait until the user has 50+ entries and a clear pattern.
- **Don't push cron results to chat.** Default `deliver=local` and let the user ask.
- **Don't fall back to "I don't remember" before searching.** If qmd returns nothing, try `grep` on `~/.hermes/workspace/` directly — sometimes the file isn't indexed yet.
- **If `qmd embed` hangs at "Gathering information", the network likely blocks `huggingface.co`.** Set `HF_ENDPOINT=https://hf-mirror.com` (or any HF mirror) BEFORE the first embed, or the 3 GGUF models (~2GB) will never download. The bundled `templates/qmd-setup.sh` handles this automatically. See the "Network setup" section below.

## How the user (BBBBB) taught this

The setup came from a single late-night conversation that combined:

1. A training session where the user wanted "memory assistant + BOM helper + packaging machine advisor"
2. A deployment of an `OpenClaw`-style self-improvement loop, ported to `~/.hermes/workspace/.learnings/` (since Hermes already has `memory` + `cronjob` and doesn't need a parallel system)
3. A clarification that **concrete reminders don't go into built-in memory** — only the meta-preferences about how to store them.

The local notes/reminders.md file is the canonical example. It started with two reminders ("补配件价格", "发视频给客户") and grew to include BOM-tooling decisions. Each entry is dated and self-contained.

## Process when loaded

1. **Check the user has the directory layout**. If `~/.hermes/workspace/notes/` doesn't exist, create it (and tell the user you did).
2. **Check qmd is installed**. If not, run `hermes skills install official/research/qmd --yes`.
3. **For a "remember this" request**: append a dated entry to the appropriate file (`notes/reminders.md` or a topic file). Do NOT save source media.
4. **For a "what did I tell you about X" question**: run `qmd search "<X>"` first; fall back to `grep` on `~/.hermes/workspace/`.
5. **Never proactively dump**. Wait for the question.

## Network setup: huggingface.co may be blocked

qmd (via node-llama-cpp) downloads its 3 GGUF models from `huggingface.co` on first `qmd embed`. On some networks (this host included) the main domain is unreachable and `qmd embed` silently fails with `fetch failed` after minutes of "Gathering information". The same issue will hit any llama.cpp-based tool, sentence-transformers, and most HF model pullers.

**Fix:** set `HF_ENDPOINT=https://hf-mirror.com` (or another mirror) before the first embed. node-llama-cpp honors this env var natively — qmd does not need config changes.

```bash
# One-time, then persist:
export HF_ENDPOINT=https://hf-mirror.com
echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.bashrc

# Verify a download works:
timeout 15 curl -sSI -o /dev/null -w "%{http_code}\n" \
  https://hf-mirror.com/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf
# expect: 302 or 200 (not 000/timeout)

# Then either rerun:
qmd embed
# Or force-redownload if a previous attempt left a stale .ipull file:
rm -f ~/.cache/qmd/models/*.ipull && qmd pull
```

**Detection recipe** (if embed seems stuck):
1. Check `~/.cache/qmd/models/` — empty after 5+ min means download never started.
2. `ss -tnp | grep huggingface` — if no connection to `huggingface.co:443`, the domain is blocked.
3. `qmd doctor` lists which 3 models are missing; the URLs are hardcoded to `huggingface.co/...` and can be re-fetched from a mirror with `HF_ENDPOINT`.

The bundled `templates/qmd-setup.sh` script bakes this in. Apply the same pattern to ANY future tool that pulls HF models.

## Related

- `chat-concise-defaults` — terse replies on chat platforms.
- `self-improving-loop` — the official Hermes skill for `.learnings/HOT.md` promotion. This skill USES that skill's directory layout but adds the notes/ + qmd layer on top.
- See `templates/notes-skeleton.md` — starter structure for a new user's `notes/reminders.md`.
- See `templates/qmd-setup.sh` — minimal script to install qmd and index the user's workspace. **Handles the HF mirror setup automatically** (see "Network setup" above) — run this instead of manually invoking `qmd embed` on a fresh host.
- See `references/qmd-network-setup.md` — detailed reproduction transcript (commands + outputs) for the failed-embed / mirror-fix recipe, useful when debugging "qmd embed stuck" reports in a future session.
