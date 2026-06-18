# Hermes Agent — Backup & Recovery

Backup of Hermes Agent skills, workspace tools, config, and recovery instructions.

## Structure

```
skills/              — 33 skills (~12MB)
workspace/           — CAD tools, notes, learnings, recovery guide
config.yaml          — Hermes config (API keys masked)
hermes-backup/       — Rolling memory snapshots (keep last 10)
```

## Restore

On a new server, read `hermes-backup/<latest>/HERMES_RECOVERY.md` and the agent will execute step by step.

## Rolling Versions

Memory and recovery snapshots are versioned by timestamp. Only the 10 most recent are retained.
