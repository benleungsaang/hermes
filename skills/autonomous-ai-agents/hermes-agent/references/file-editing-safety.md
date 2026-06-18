# File Editing Safety — write_file vs patch

> Captured 2026-06-17 after the agent used `write_file` to "add a
> new chapter" to AGENTS.md and **silently overwrote 7+ existing
> chapters** (Reminders classification, memory-helper workflow,
> WeChat writing rules, secondary-model workflow, etc.). Recovery
> was possible because qmd had embedded the file, but it cost 10+
> tool calls and a self-correction entry in `.learnings/corrections.md`.

## The two file-editing tools — what each does

| Tool | Behavior | Risk |
|---|---|---|
| `write_file(path, content)` | **Overwrites the entire file** with `content`. Creates parent directories. | **DESTRUCTIVE.** Any existing content not included in `content` is lost. |
| `patch(path, old_string, new_string)` | **Find-and-replace** on a single occurrence (or all, with `replace_all=True`). Returns a diff. | **SAFE.** Fails loudly if `old_string` is not unique, so you discover the mistake immediately. |

## Decision rule

**Default to `patch`.** Use `write_file` only when **all** of these hold:

1. The file does not yet exist (creating from scratch)
2. The file is a pure scratch file (e.g. `/tmp/...` that won't be reused)
3. The file is a known template you're regenerating from a fixed source

**Never** use `write_file` to "add a section to an existing long-form document" without first reading the entire file and reconstructing it byte-for-byte + your addition. The chance of silently dropping a section is too high.

## The AGENTS.md incident (2026-06-17)

What happened:

```python
# Intent: add a "Secondary Model Workflow" chapter to AGENTS.md
# Mistake:
write_file(path="~/.hermes/workspace/AGENTS.md", content=secondary_model_workflow_text)
# Result: AGENTS.md now contains ONLY the new chapter (163 lines → 64 lines).
# Lost: Reminders 分类规则, 记忆助手工作流, 微信 PC 端写作规范, etc.
```

How it could have been prevented:

```python
# Option A (preferred): read the whole file, append, write back
existing = read_file(path="~/.hermes/workspace/AGENTS.md")
new_content = existing + "\n\n## 协助模型工作流\n\n" + workflow_text
write_file(path="~/.hermes/workspace/AGENTS.md", content=new_content)

# Option B (preferred for additions): append via patch
patch(path="~/.hermes/workspace/AGENTS.md",
      old_string="### 不调用的场景\n\n- ...",
      new_string="### 不调用的场景\n\n- ...\n\n## 新章节标题\n\n...")

# Option C (preferred when the addition is at end of file): shell append
# echo -e "\n## 新章节\n..." >> ~/.hermes/workspace/AGENTS.md
```

## Recovery recipe

If you discover an overwrote file with content worth saving:

1. **Don't panic-write.** The qmd index likely has embedded chunks for the old file. If the index was updated after the last write, the old content is recoverable via `qmd search`.
2. **Check git.** If the file is in a git repo, `git show HEAD:path/to/file` gives you the previous version.
3. **Check the conversation log.** Past tool results often echo the file contents.
4. **Reconstruct from pieces.** Once you have the recovered content, write it back with `write_file` (now safe because the destination is being created, not overwritten-with-content).

After recovery, append a `corrections.md` entry so future sessions know to default to `patch`.

## Other places where `write_file` is unsafe

The lesson generalises. Any file with multiple distinct sections added by different sessions can be silently destroyed by an over-eager `write_file`:

- `AGENTS.md`, `SOUL.md`, `HOT.md` — user-facing rule files
- `MAINTENANCE.md` — maintenance log
- `notes/reminders.md` — the two-track reminder list
- `notes/feedback-<model>.md` — append-only feedback log
- `notes/<model>_ledger.md` — append-only cost ledger
- `.learnings/corrections.md`, `LEARNINGS.md`, `ERRORS.md`, `PREFERENCES.md` — append-only logs

For all of these, default to `patch` (find a unique anchor line, replace with the old + new section) or shell `>>` append.

## When `write_file` IS the right tool

- Creating a brand new file (`/tmp/...`, `notes/<new_topic>.md` for a topic that didn't exist before).
- Re-generating a template from a fixed source (e.g. updating the cost script after a pricing change — the whole file is small and known).
- After a recovery operation where the destination is being created, not overwritten.

If you're unsure, **read the file first**, then decide. The read costs almost nothing; the over-write costs the entire file.

## Related

- Parent skill: `hermes-agent` — this reference is for code-assist agents editing long-form documents under `~/.hermes/workspace/`.
- `chat-concise-defaults` — covers related output-style rules (don't dump, wait for question), separate concern.
- The 2026-06-17 incident is also recorded in `~/.hermes/workspace/.learnings/corrections.md` for cross-session self-improvement.
