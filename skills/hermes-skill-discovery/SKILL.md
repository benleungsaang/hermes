---
name: hermes-skill-discovery
description: "Correctly discover, verify, install, and avoid hallucinating Hermes skills. Covers the 3-tier source model (builtin/official-hub/community-hub), the install-identifier syntax, the search-before-trust workflow, and the diagnostic recipe when a skill name looks plausible but doesn't exist. Apply when the user asks to install a skill, mentions a specific skill name, or you suspect an LLM-hallucinated skill identifier."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, discovery, install, anti-hallucination, hermes-cli]
    category: software-development
---

# Hermes Skill Discovery

Stop guessing. Stop naming skills after the library they would use. This skill governs how to correctly look up, verify, and install Hermes skills — and how to recognise the AI-hallucinated skill name when you see one.

## When to use this skill

Load when ANY of these signals appear:

- User asks to install a skill (`hermes skills install ...`)
- User mentions a specific skill name and you want to verify it exists
- You or another LLM just named a skill that looks "too perfect" — e.g. `<library>-<verb>` patterns like `ezdxf-dwg-parse`, `excel-bom-writer`, `pandas-data-clean`
- User asks "what skills do I have" / "what can I install"
- The user (or a doc, or another LLM) suggests installing a skill without giving a URL

## The 3-tier source model

Hermes skills come from three sources. They are NOT equivalent — they differ in trust, freshness, and naming convention.

| Tier | Source | Trust | Naming | Discovery command |
|---|---|---|---|---|
| 1. Builtin | Bundled with `hermes-agent` (e.g. `hermes-agent`, `chat-concise-defaults`, `humanizer`) | High — Nous-maintained | Single word or hyphenated domain noun | `hermes skills list` |
| 2. Official Hub | `official/<category>/<name>` (currently 100 skills in `Nous Research` hub) | High — official, but optional | `<library>` or `<library>-<feature>` (e.g. `duckduckgo-search`, `excel-author`) | `hermes skills browse --source official` |
| 3. Community Hub | `skills-sh/<owner>/<repo>/<path>` or `clawhub/...`, `lobehub/...`, `github/...` | Variable — read scan verdict | Free-form (often matches the source repo's own naming) | `hermes skills browse --source <source>` |

The local install set is a SUBSET of any of these. Just because a skill isn't on `hermes skills list` doesn't mean it doesn't exist — you have to look in the hub.

## Anti-hallucination checklist

Before installing a skill name that came from the user, a doc, or another LLM:

1. **Run `hermes skills search <keyword>`** with the most distinctive token. A `MEDIUM` timeout means the hub is slow — wait, don't assume "not found".
2. **Run `hermes skills browse --source official`** for the canonical 100. If the skill isn't there, it's not official.
3. **If the search returns nothing AND the user is convinced the skill exists**, ask the user for the source URL or repo path. Most "AI-hallucinated skill names" come from LLMs naming what the skill *would* be called if it existed, not what it's actually called.
4. **If the skill name pattern is `<library>-<verb>`** (e.g. `pandas-load-csv`, `ezdxf-dwg-parse`, `fastapi-auth-middleware`), suspect hallucination. Real skill names tend to use the library or feature noun, not library+verb composites.
5. **Once installed, the SKILL.md lives at `~/.hermes/skills/<category>/<name>/SKILL.md`** (builtin) or under `~/.hermes/skills/` directly (hub-installed). Use `hermes skills list` to confirm the install path.

## The install command — gotchas

- `hermes skills install <id> --yes` — single identifier only. NO multi-id positional install. Run it N times for N skills.
- Identifier format for official: `official/<category>/<name>` (e.g. `official/research/qmd`). Use `hermes skills inspect <id>` to preview without installing.
- Identifier format for community: `skills-sh/<owner>/<repo>/<skill-path>` or just the bare name if unique. Search to confirm.
- The install runs a security scan (`Scan: ... Verdict: SAFE / DANGEROUS / BLOCKED`). `ALLOWED` after `DANGEROUS` is fine; `BLOCKED` cannot be overridden except with `--force`.
- TUI mode requires `-y` / `--yes` to skip the confirm prompt.

## Diagnostic recipe for "this skill doesn't exist"

When the user reports a skill name that doesn't search or browse:

1. **Acknowledge cleanly.** "I checked official + search; that exact name isn't in the hub. Possible reasons: AI-hallucinated, wrong source, or new and not indexed yet."
2. **Search 2-3 variants.** Drop the verb (`qmd` vs `web-search`), try the library (`ezdxf`, `dxf`), try synonyms (`bom`, `bills-of-materials`).
3. **Offer the python-library fallback.** If the skill was supposed to wrap a Python library (ezdxf, pandas, openpyxl), tell the user the library can be installed directly and used from `execute_code` without a skill. This is often the actual right answer.
4. **Ask for the source.** If the user insists it exists, ask for the GitHub URL or repo path. `hermes skills install <github-url>` accepts a direct HTTPS URL to a SKILL.md.

## Pitfalls

- **Don't auto-install**. Always `inspect` (or `search`) first, then `install` with explicit user confirmation in non-TUI mode.
- **Don't trust LLM-suggested skill names without verification**. They are pattern-completing, not lookups.
- **Don't conflate "local installed" with "all available"**. `hermes skills list` shows installed; `browse --source official` shows the full official catalog (100 skills).
- **Timeouts are not "not found"**. `hermes skills search` can hit the 60s timeout. Retry, or browse with `--source` instead.
- **Don't write a new skill when the library exists**. If the user wants to "read DWG and output Excel," the answer is `pip install ezdxf openpyxl`, not a new skill that wraps them. Skills add workflow glue; they don't replace Python packages.

## How the user taught this

A session where the user asked to install `ezdxf-dwg-parse` and `excel-bom-writer` revealed that even confident-sounding skill names from LLMs can be hallucinated. The names followed the `<library>-<verb>` pattern that almost no real Hermes skill uses. Confirming via `search` + `browse --source official` is the only reliable check.

## Process when loaded

1. **Identify the tier** the skill is expected to come from. Check builtin first (fastest).
2. **Search + browse**. Cover both the keyword search and the relevant `--source` browse.
3. **If found**: `inspect` to preview, `install --yes` to confirm.
4. **If not found**: run the anti-hallucination diagnostic, propose the python-library fallback, ask for the source URL.
5. **Never assume**: a skill exists because the user mentioned it, because a doc referenced it, or because another LLM named it.

## Related

- `chat-concise-defaults` — terse replies when the user is on a chat platform; pairs well with this skill when reporting "skill not found."
- See `references/skill-install-commands.md` — copy-paste recipes for common install patterns (single skill, multi-skill batch, force-install, uninstall).
