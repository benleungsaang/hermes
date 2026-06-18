---
name: qmd
description: "Search personal knowledge bases, notes, docs, and meeting transcripts locally using qmd (BM25 + optional vector / rerank). For fast personal-note recall, default to `qmd search` (BM25 only, sub-second, no model load) — only escalate to `qmd vsearch` or `qmd query` when the user explicitly wants semantic ranking and the host has GPU / multi-core CPU. Index once with `qmd collection add` + `qmd embed`, then `qmd search` for every recall. Use when the user asks 'search my notes', 'what did I tell you about X', 'find in my docs', or wants any cross-session recall over their markdown knowledge base."
version: 1.0.0
author: Hermes Agent + Teknium
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Search, Knowledge-Base, RAG, Notes, MCP, Local-AI]
    related_skills: [obsidian, native-mcp, arxiv]
---

# QMD — Query Markup Documents

Local, on-device search engine for personal knowledge bases. Indexes markdown
notes, meeting transcripts, documentation, and any text-based files, then
provides hybrid search combining keyword matching, semantic understanding, and
LLM-powered reranking — all running locally with no cloud dependencies.

Created by [Tobi Lütke](https://github.com/tobi/qmd). MIT licensed.

## When to Use

- User asks to search their notes, docs, knowledge base, or meeting transcripts
- User wants to find something across a large collection of markdown/text files
- User wants semantic search ("find notes about X concept") not just keyword grep
- User has already set up qmd collections and wants to query them
- User asks to set up a local knowledge base or document search system
- Keywords: "search my notes", "find in my docs", "knowledge base", "qmd"

## Prerequisites

### Node.js >= 22 (required)

```bash
# Check version
node --version  # must be >= 22

# macOS — install or upgrade via Homebrew
brew install node@22

# Linux — use NodeSource or nvm
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
# or with nvm:
nvm install 22 && nvm use 22
```

### SQLite with Extension Support (macOS only)

macOS system SQLite lacks extension loading. Install via Homebrew:

```bash
brew install sqlite
```

### Install qmd

```bash
npm install -g @tobilu/qmd
# or with Bun:
bun install -g @tobilu/qmd
```

First run auto-downloads 3 local GGUF models (~2GB total):

| Model | Purpose | Size |
|-------|---------|------|
| embeddinggemma-300M-Q8_0 | Vector embeddings | ~300MB |
| qwen3-reranker-0.6b-q8_0 | Result reranking | ~640MB |
| qmd-query-expansion-1.7B | Query expansion | ~1.1GB |

### Verify Installation

```bash
qmd --version
qmd status
```

## Quick Reference

| Command | What It Does | Speed (GPU / multi-core) | Speed (CPU 1-core / VM) |
|---------|-------------|-------------------------|------------------------|
| `qmd search "query"` | BM25 keyword search (no models) | ~0.2s | ~0.4s ✅ |
| `qmd vsearch "query"` | Semantic vector search (1 model) | ~3s | ~10-30s |
| `qmd query "query"` | Hybrid + reranking (all 3 models) | ~2-3s warm, ~19s cold | **2-5 minutes** — see warning below |

**⚠️ Latency figures are host-dependent.** The "~2-3s warm" for `qmd query`
assumes a GPU (Metal/CUDA/Vulkan) or multi-core CPU. On a 1-vCPU VM (this
host included), `qmd query` routinely takes 2-5+ minutes per call because
all 3 GGUF models are loaded and run sequentially on one core. **Do not
quote "2-3s warm" without checking the host.** Default to `qmd search` for
personal-note recall; treat `qmd query` as a debug-tier tool, not a daily
driver, on constrained hosts.
| `qmd get <docid>` | Retrieve full document content | instant |
| `qmd multi-get "glob"` | Retrieve multiple files | instant |
| `qmd collection add <path> --name <n>` | Add a directory as a collection | instant |
| `qmd context add <path> "description"` | Add context metadata to improve retrieval | instant |
| `qmd embed` | Generate/update vector embeddings | varies |
| `qmd status` | Show index health and collection info | instant |
| `qmd mcp` | Start MCP server (stdio) | persistent |
| `qmd mcp --http --daemon` | Start MCP server (HTTP, warm models) | persistent |

## Setup Workflow

### 1. Add Collections

Point qmd at directories containing your documents:

```bash
# Add a notes directory
qmd collection add ~/notes --name notes

# Add project docs
qmd collection add ~/projects/myproject/docs --name project-docs

# Add meeting transcripts
qmd collection add ~/meetings --name meetings

# List all collections
qmd collection list
```

### 2. Add Context Descriptions

Context metadata helps the search engine understand what each collection
contains. This significantly improves retrieval quality:

```bash
qmd context add qmd://notes "Personal notes, ideas, and journal entries"
qmd context add qmd://project-docs "Technical documentation for the main project"
qmd context add qmd://meetings "Meeting transcripts and action items from team syncs"
```

### 3. Generate Embeddings

```bash
qmd embed
```

This processes all documents in all collections and generates vector
embeddings. Re-run after adding new documents or collections.

### 4. Verify

```bash
qmd status   # shows index health, collection stats, model info
```

## Search Patterns

### Fast Keyword Search (BM25)

Best for: exact terms, code identifiers, names, known phrases.
No models loaded — near-instant results.

```bash
qmd search "authentication middleware"
qmd search "handleError async"
```

### Semantic Vector Search

Best for: natural language questions, conceptual queries.
Loads embedding model (~3s first query).

```bash
qmd vsearch "how does the rate limiter handle burst traffic"
qmd vsearch "ideas for improving onboarding flow"
```

### Hybrid Search with Reranking (Best Quality)

Best for: important queries where quality matters most.
Uses all 3 models — query expansion, parallel BM25+vector, reranking.

```bash
qmd query "what decisions were made about the database migration"
```

### Structured Multi-Mode Queries

Combine different search types in a single query for precision:

```bash
# BM25 for exact term + vector for concept
qmd query $'lex: rate limiter\nvec: how does throttling work under load'

# With query expansion
qmd query $'expand: database migration plan\nlex: "schema change"'
```

### Query Syntax (lex/BM25 mode)

| Syntax | Effect | Example |
|--------|--------|---------|
| `term` | Prefix match | `perf` matches "performance" |
| `"phrase"` | Exact phrase | `"rate limiter"` |
| `-term` | Exclude term | `performance -sports` |

### HyDE (Hypothetical Document Embeddings)

For complex topics, write what you expect the answer to look like:

```bash
qmd query $'hyde: The migration plan involves three phases. First, we add the new columns without dropping the old ones. Then we backfill data. Finally we cut over and remove legacy columns.'
```

### Scoping to Collections

```bash
qmd search "query" --collection notes
qmd query "query" --collection project-docs
```

### Output Formats

```bash
qmd search "query" --json        # JSON output (best for parsing)
qmd search "query" --limit 5     # Limit results
qmd get "#abc123"                # Get by document ID
qmd get "path/to/file.md"       # Get by file path
qmd get "file.md:50" -l 100     # Get specific line range
qmd multi-get "journals/*.md" --json  # Batch retrieve by glob
```

## MCP Integration (Recommended)

qmd exposes an MCP server that provides search tools directly to
Hermes Agent via the native MCP client. This is the preferred
integration — once configured, the agent gets qmd tools automatically
without needing to load this skill.

### Option A: Stdio Mode (Simple)

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  qmd:
    command: "qmd"
    args: ["mcp"]
    timeout: 30
    connect_timeout: 45
```

This registers tools: `mcp_qmd_search`, `mcp_qmd_vsearch`,
`mcp_qmd_deep_search`, `mcp_qmd_get`, `mcp_qmd_status`.

**Tradeoff:** Models load on first search call (~19s cold start),
then stay warm for the session. Acceptable for occasional use.

### Option B: HTTP Daemon Mode (Fast, Recommended for Heavy Use)

Start the qmd daemon separately — it keeps models warm in memory:

```bash
# Start daemon (persists across agent restarts)
qmd mcp --http --daemon

# Runs on http://localhost:8181 by default
```

Then configure Hermes Agent to connect via HTTP:

```yaml
mcp_servers:
  qmd:
    url: "http://localhost:8181/mcp"
    timeout: 30
```

**Tradeoff:** Uses ~2GB RAM while running, but every query is fast
(~2-3s). Best for users who search frequently.

### Keeping the Daemon Running

#### macOS (launchd)

```bash
cat > ~/Library/LaunchAgents/com.qmd.daemon.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.qmd.daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>qmd</string>
    <string>mcp</string>
    <string>--http</string>
    <string>--daemon</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/qmd-daemon.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/qmd-daemon.log</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.qmd.daemon.plist
```

#### Linux (systemd user service)

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/qmd-daemon.service << 'EOF'
[Unit]
Description=QMD MCP Daemon
After=network.target

[Service]
ExecStart=qmd mcp --http --daemon
Restart=on-failure
RestartSec=10
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now qmd-daemon
systemctl --user status qmd-daemon
```

### MCP Tools Reference

Once connected, these tools are available as `mcp_qmd_*`:

| MCP Tool | Maps To | Description |
|----------|---------|-------------|
| `mcp_qmd_search` | `qmd search` | BM25 keyword search |
| `mcp_qmd_vsearch` | `qmd vsearch` | Semantic vector search |
| `mcp_qmd_deep_search` | `qmd query` | Hybrid search + reranking |
| `mcp_qmd_get` | `qmd get` | Retrieve document by ID or path |
| `mcp_qmd_status` | `qmd status` | Index health and stats |

The MCP tools accept structured JSON queries for multi-mode search:

```json
{
  "searches": [
    {"type": "lex", "query": "authentication middleware"},
    {"type": "vec", "query": "how user login is verified"}
  ],
  "collections": ["project-docs"],
  "limit": 10
}
```

## CLI Usage (Without MCP)

When MCP is not configured, use qmd directly via terminal:

```
terminal(command="qmd query 'what was decided about the API redesign' --json", timeout=30)
```

For setup and management tasks, always use terminal:

```
terminal(command="qmd collection add ~/Documents/notes --name notes")
terminal(command="qmd context add qmd://notes 'Personal research notes and ideas'")
terminal(command="qmd embed")
terminal(command="qmd status")
```

## How the Search Pipeline Works

Understanding the internals helps choose the right search mode:

1. **Query Expansion** — A fine-tuned 1.7B model generates 2 alternative
   queries. The original gets 2x weight in fusion.
2. **Parallel Retrieval** — BM25 (SQLite FTS5) and vector search run
   simultaneously across all query variants.
3. **RRF Fusion** — Reciprocal Rank Fusion (k=60) merges results.
   Top-rank bonus: #1 gets +0.05, #2-3 get +0.02.
4. **LLM Reranking** — qwen3-reranker scores top 30 candidates (0.0-1.0).
5. **Position-Aware Blending** — Ranks 1-3: 75% retrieval / 25% reranker.
   Ranks 4-10: 60/40. Ranks 11+: 40/60 (trusts reranker more for long tail).

**Smart Chunking:** Documents are split at natural break points (headings,
code blocks, blank lines) targeting ~900 tokens with 15% overlap. Code
blocks are never split mid-block.

## Lean usage for personal knowledge bases (2026-06-17)

When `qmd` is used as the backend for a user's personal notes / reminders
/ cross-session recall (the typical `hermes-personal-knowledge-loop`
case), the agent's job is **fast fuzzy recall over a few hundred short
markdown files**, not state-of-the-art IR over a 10M-document corpus.
Apply these rules by default:

- **Use `qmd search` for almost every recall.** It's BM25-only, no model
  load, sub-second. Chinese works out of the box.
- **Don't escalate to `qmd vsearch` / `qmd query` unless the user asks
  for "better quality" or `qmd search` returns nothing useful across
  2–3 reformulations.** Each escalation loads 1–3 GGUF models.
- **If the user has asked for a CPU-only / lightweight / "simple"
  setup**, never auto-promote to `qmd query` — its 2–5 minute latency
  on a 1-core VM is unacceptable for personal-note recall.
- **If `qmd search` returns no matches, say so.** Don't fall back to
  fabricating plausible-sounding snippets, paraphrasing the question
  into a query the agent thinks "should" match, or claiming the answer
  is in memory. The user's preference (2026-06-17): "你搜索不到就告诉
  我搜索不到，再提供全部内容/相似内容，我自己肉眼筛选也可以". So
  the protocol is: `qmd search` → no hit → tell the user → optionally
  list the files in the matching collection so they can read manually.
- **Index maintenance is the agent's job, not the user's.** After
  editing any `.md` file in an indexed collection, run `qmd update`
  then `qmd embed` (or just `qmd update` if the change is only
  metadata). Don't expect the user to remember.

## Best Practices

1. **Always add context descriptions** — `qmd context add` dramatically
   improves retrieval accuracy. Describe what each collection contains.
2. **Re-embed after adding documents** — `qmd embed` must be re-run when
   new files are added to collections.
3. **Use `qmd search` for speed** — when you need fast keyword lookup
   (code identifiers, exact names), BM25 is instant and needs no models.
4. **Use `qmd query` for quality** — when the question is conceptual or
   the user needs the best possible results, use hybrid search.
5. **Prefer MCP integration** — once configured, the agent gets native
   tools without needing to load this skill each time.
6. **Daemon mode for frequent users** — if the user searches their
   knowledge base regularly, recommend the HTTP daemon setup.
7. **First query in structured search gets 2x weight** — put the most
   important/certain query first when combining lex and vec.

### Troubleshooting

### "Models downloading on first run"
Normal — qmd auto-downloads ~2GB of GGUF models on first use.
This is a one-time operation.

### Model download fails with `fetch failed` / `ETIMEDOUT` (199.59.148.206)
Symptom: `qmd pull` or first `qmd embed` hangs on "Gathering information"
then errors out with `ETIMEDOUT 199.59.148.206:443` (Cloudflare / huggingface.co).

Cause: outbound to `huggingface.co` is blocked or unstable from the host
network (corporate proxy, region, captive portal, etc.).

Fix: qmd respects the standard `HF_ENDPOINT` env var from node-llama-cpp.
Point it at the HuggingFace mirror before any `qmd pull` / `qmd embed`:

```bash
export HF_ENDPOINT=https://hf-mirror.com   # HF官方国内镜像
qmd pull
qmd embed
```

Persist this in `~/.bashrc` (or equivalent shell rc) so every future shell
inherits it — `qmd` does NOT read `HF_ENDPOINT` from any config file, only
the live environment. Without the env var set, every invocation will re-hang
and re-fail on the blocked host.

Verify the mirror is reachable from your host first:

```bash
curl -sSI -o /dev/null -w "%{http_code} %{time_total}s\n" \
  https://hf-mirror.com/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf
# expect: 302, < 1s
```

### `qmd update` crashes with `ENOTDIR ... AGENTS.md` (or any single file)
Symptom: `qmd update` exits non-zero with
`Error: ENOTDIR: not a directory, scandir '/path/to/some/file.md'`.

Cause: a collection was added with a path pointing to a single FILE
instead of a directory. `qmd` treats the path as a directory and tries
to `scandir()` it; the OS returns `ENOTDIR`.

Fix: collections MUST point at directories. List and remove the bad
collection, then re-add the parent directory:

```bash
qmd collection list                  # find the offender
qmd collection remove <bad-name>     # delete it
qmd collection add <parent-dir> --name <name>
qmd update && qmd embed
```

### `qmd collection add /path/to/single-file.md --name foo` will appear
to succeed (`collection add` is permissive), but `qmd update` is the
function that actually walks the path with `scandir()` and explodes. So
"the add worked" does not mean "the collection is valid."

### `qmd collection add` on `.xlsx` / `.pdf` / `.docx` / `.pptx` silently does nothing
Symptom: user drops a spreadsheet or PDF into the workspace and asks
"建索引" / "search it". The agent calls `qmd collection add <path>
--name <n>` which **appears to succeed** (no error), but `qmd status`
shows the new collection with 0 files, and `qmd search` returns nothing
when the user queries for spreadsheet content.

Cause: `qmd`'s collection glob is `**/*.md` (hard-coded pattern for
markdown). xlsx / pdf / docx / pptx / csv / xls / images are all
silently skipped. The collection "adds" but the file filter rejects
every non-md file. No error is raised because the directory was
technically scanned — it just had 0 matching files.

Fix for binary formats — **do not use `qmd collection add`**. Use the
purpose-built path:

| Format | Read with |
|---|---|
| `.xlsx` / `.xlsm` | `execute_code` with `openpyxl` (or `read_file` — both extract structured data) |
| `.pdf` | `read_file` (auto-extracts) or `ocr-and-documents` skill (marker-pdf) |
| `.docx` | `read_file` (auto-extracts) |
| `.pptx` | `powerpoint` skill |
| `.csv` / `.tsv` | `read_file` |
| Images | `vision_analyze` |

**Operational rule for the user-facing reply:** when the user says
"建索引" / "search my files" / "找一下那份表格", first check if the
target is a `.md` file (qmd works great). If it's binary, tell them
"qmd 不索引 Excel / PDF（只索引 .md），我用 openpyxl 现场读" — and
read it directly.

**EXCEPTION — user override (added 2026-06-17):** When the user
**explicitly** says "转成 md" / "方案A" / "丢进 qmd 索引", then
the conversion is valid and preferred. The flow is:

1. Read the binary with `execute_code` + openpyxl
2. Convert to markdown table (preserve key columns, drop noise)
3. `write_file` to a path inside an existing qmd collection
   (`~/.hermes/workspace/.learnings/domains/<name>.md` is the
   usual destination for personal knowledge)
4. `qmd update` (and `qmd embed` if the collection is vector-indexed)
5. From then on, `qmd search` does the lookup

This is how the 包装机价格表 (packaging-machine-price-table.md)
is handled — B explicitly chose this over the live-xlsx pattern.
The "don't convert" rule is for default behavior; explicit user
direction overrides it.

**The "do not convert" framing of the default rule was misleading.**
The real distinction is: **qmd can't index binary** (it hard-codes
`**/*.md`); but the agent CAN convert and write, when the user
asks. Don't refuse a conversion request by citing this section.

Reference: 2026-06-17 — B asked "建索引" for `确认型号价格表.xlsx`;
the agent wasted a turn trying `qmd collection add` before realizing
qmd silently skipped it. The fix is in the recipe above.

### `qmd search` returns nothing for short unit tokens like "1.6L" / "10头" / "25kg" (added 2026-06-17)

**Symptom:** The user asks "VP-BF-180-06U 带什么秤" — you `qmd search "10头1.6L 多头秤"` and it works. But `qmd search "1.6L"` alone returns 0 hits, and `qmd search "10头"` alone returns 0 hits, even though the row in the markdown file clearly contains those exact substrings.

**Root cause:** BM25 (SQLite FTS5) tokenizes on whitespace and punctuation. `"1.6L"` is one token. `"10头"` is one token. Neither matches the FTS5 inverted index well because:

- `"1.6L"` is rarely a search query by itself; users type `"1.6L 多头秤"` or `"VP-BF-180-06U"`
- `"10头"` mixes ASCII digit + Chinese char; FTS5's default tokenizer handles it as a single token, but the score can be dampened by short-token heuristics
- Pure numeric / hybrid short tokens are the **worst** BM25 inputs

**Fix — search by:**
1. **Model code first** (always works): `qmd search "GDS180-06U"` → 60%+
2. **Multi-keyword Chinese phrase**: `qmd search "10头 1.6"` (split on punctuation, use space between Chinese phrases) → 50%+
3. **Column header + value**: `qmd search "标配组合秤 10"` → 40%+

What does NOT work:
- `qmd search "1.6L"` (single unit token) → 0%
- `qmd search "10头"` (single mixed-script token) → 0%
- `qmd search "1.6"` alone (numeric only) → 0% unless there's a long row of digits

**When you get 0 hits, do NOT conclude "data missing".** Reformulate the query once with a model code or multi-keyword phrase. If still 0, then the data is actually missing.

### `qmd query` takes minutes / times out on CPU-only hosts
Symptom: `qmd query "..."` times out at 60-120s and returns no results,
even though all three models are downloaded and `qmd doctor` shows them
as valid.

Cause: hybrid `qmd query` loads **all three** GGUF models into RAM and
runs query expansion (1.7B) + reranking (0.6B) on every call. On a CPU
single-core host (e.g. 1 vCPU / 1 math core), each query takes 2-5+
minutes. The "2-3s warm" figure in this skill assumes real hardware
(Metal / CUDA / Vulkan, multi-core). On a constrained VM, that figure
is wrong by ~100x.

Mitigation for CPU-only hosts:
- Default to `qmd search` (BM25 only) — instant, no model load.
- `qmd vsearch` (single embedding model) is acceptable — ~3s typical.
- `qmd query` is impractical until the host has a GPU or you accept
  2-5 minute latencies.

Tell the user this when recommending `qmd query` on a constrained host.
Do NOT claim "~2-3s warm" without checking the host has more than 1 core.

### Cold start latency (~19s)
This happens when models aren't loaded in memory. Solutions:
- Use HTTP daemon mode (`qmd mcp --http --daemon`) to keep warm
- Use `qmd search` (BM25 only) when models aren't needed
- MCP stdio mode loads models on first search, stays warm for session

### macOS: "unable to load extension"
Install Homebrew SQLite: `brew install sqlite`
Then ensure it's on PATH before system SQLite.

### "No collections found"
Run `qmd collection add <path> --name <name>` to add directories,
then `qmd embed` to index them.

### Embedding model override (CJK/multilingual)
Set `QMD_EMBED_MODEL` environment variable for non-English content:
```bash
export QMD_EMBED_MODEL="your-multilingual-model"
```

## Data Storage

- **Index & vectors:** `~/.cache/qmd/index.sqlite`
- **Models:** Auto-downloaded to local cache on first run
- **No cloud dependencies** — everything runs locally

## References

- [GitHub: tobi/qmd](https://github.com/tobi/qmd)
- [QMD Changelog](https://github.com/tobi/qmd/blob/main/CHANGELOG.md)
