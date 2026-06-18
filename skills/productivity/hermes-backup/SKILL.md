---
name: hermes-backup
description: Backup Hermes skills, workspace, config and memory snapshots to GitHub. Rolling 10 versions.
---

# Hermes Backup to GitHub

Backup skills, workspace, config.yaml (de-sensitized), and create a dated memory snapshot to GitHub with rolling retention (10 versions).

## Prerequisites

- GitHub personal access token with repo scope, stored in `~/.hermes/.env` as `HERMES_BACKUP_TOKEN`
- Repo URL: `https://github.com/benleungsaang/hermes.git`

## Step 1 — Clone if not exists

```bash
if [ ! -d ~/hermes-backup/.git ]; then
    git clone https://github.com/benleungsaang/hermes.git ~/hermes-backup
fi
```

## Step 2 — Update skills and workspace

```bash
cd ~/hermes-backup
rm -rf skills
cp -r ~/.hermes/skills skills
find skills -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
rm -rf workspace/cad-bom workspace/notes workspace/.learnings workspace/hermes-recovery
cp -r ~/.hermes/workspace/cad-bom workspace/cad-bom
cp -r ~/.hermes/workspace/notes workspace/notes
cp -r ~/.hermes/workspace/.learnings workspace/.learnings
cp -r ~/.hermes/workspace/hermes-recovery workspace/hermes-recovery
find workspace -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
sed 's/api_key:.*/api_key: "***"/g; s/token:.*/token: "***"/g' ~/.hermes/config.yaml > config.yaml
```

## Step 3 — Create dated snapshot

```bash
TS=$(date -u +%Y-%m-%d_%H%M%S)
mkdir -p hermes-backup/$TS
cp workspace/hermes-recovery/memory_export*.md hermes-backup/$TS/
cp workspace/hermes-recovery/HERMES_RECOVERY.md hermes-backup/$TS/
```

## Step 4 — Prune old snapshots (keep 10)

```bash
COUNT=$(ls -d hermes-backup/20* 2>/dev/null | wc -l)
if [ "$COUNT" -gt 10 ]; then
    TO_DELETE=$((COUNT - 10))
    for d in $(ls -d hermes-backup/20* 2>/dev/null | sort | head -n $TO_DELETE); do
        rm -rf "$d"
    done
fi
```

## Step 5 — Commit and push

```bash
cd ~/hermes-backup
git add -A
git commit -m "auto-backup $(date -u +%Y-%m-%d_%H%M%S)"
TOKEN=$(grep HERMES_BACKUP_TOKEN ~/.hermes/.env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
if [ -n "$TOKEN" ]; then
    git remote set-url origin "https://benleungsaang:${TOKEN}@github.com/benleungsaang/hermes.git"
    git push origin main
    git remote set-url origin https://github.com/benleungsaang/hermes.git
else
    echo "ERROR: HERMES_BACKUP_TOKEN not found in .env"
fi
```

## Troubleshooting

- Push fails with auth error: ensure HERMES_BACKUP_TOKEN is set in ~/.hermes/.env
- Skills dir missing: confirm ~/.hermes/skills exists
- Git clone fails: check network or repo accessibility
