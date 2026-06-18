# Skill Install — Command Recipes

Copy-paste ready. Always `inspect` (or `search`) before `install`.

## Single skill — official hub

```bash
# Preview without installing
hermes skills inspect official/research/qmd

# Install (skip confirm prompt in TUI mode)
hermes skills install official/research/qmd --yes
```

## Single skill — community (skills-sh)

```bash
# Search to find the exact identifier
hermes skills search "duckduckgo"

# Install
hermes skills install skills-sh/qu-skills/skills/web-search --yes
```

## Single skill — direct GitHub URL

```bash
# If the user gives a URL to a SKILL.md
hermes skills install https://raw.githubusercontent.com/owner/repo/main/skills/foo/SKILL.md --yes
```

## Bulk — install N skills

`install` only accepts ONE identifier at a time. Loop it:

```bash
for id in official/research/duckduckgo-search \
          official/research/scrapling \
          official/finance/excel-author \
          official/research/qmd; do
  hermes skills install "$id" --yes
done
```

## Verify what's installed

```bash
hermes skills list              # local installed set
hermes skills browse --source official --size 100   # full official catalog
```

## Uninstall / reset

```bash
hermes skills uninstall <identifier>
hermes skills reset             # nuke and rebuild the local skill dir (destructive)
```

## Force install past a scan verdict

If the security scan returns `BLOCKED`, `--force` is the override. Use only when:

- You wrote the skill yourself
- The flagged content is a known false positive (e.g. `pip install` reference in the SKILL.md is benign)
- You have user consent

```bash
hermes skills install <identifier> --force --yes
```

## Diagnose "skill not found"

1. `hermes skills search <keyword>` — wait through the 60s timeout
2. `hermes skills browse --source official --size 100` — is it in the canonical 100?
3. If neither finds it → AI-hallucinated or wrong source. Ask user for the URL.

## Common error messages

| Error | Cause | Fix |
|---|---|---|
| `unrecognized arguments: 80 27` | Tried to multi-install with positional args | Run install N times, not 1 time with N args |
| `error: argument skills_action: invalid choice: 'info'` | Used `info` (not a real subcommand) | Use `inspect <identifier>` |
| `Resolution failed: timeout` | Hub slow | Retry, or browse with `--source official` |
| `Decision: BLOCKED` | Security scan rejected | Need `--force` + explicit consent, or abandon |
