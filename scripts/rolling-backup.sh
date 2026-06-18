#!/usr/bin/env bash
# Hermes Rolling Backup — run via cron to snapshot memory + workspace
set -e
REPO_DIR="$HOME/hermes-backup"      # git clone 目录
HERMES_DIR="$HOME/.hermes"
BACKUP_DIR="$REPO_DIR/hermes-backup"
MAX_VERSIONS=10

# 1. Backup current memory to workspace
MEMORY_EXPORT="$HERMES_DIR/workspace/hermes-recovery/memory_export_latest.md"
# The agent should write memory entries here before triggering this script
# Or this can be done manually

# 2. Create timestamped snapshot
TS=$(date -u +%Y-%m-%d_%H%M%S)
SNAPSHOT="$BACKUP_DIR/$TS"
mkdir -p "$SNAPSHOT"

# Copy workspace (excluding cache/pycache)
cp -r "$HERMES_DIR/workspace/cad-bom" "$SNAPSHOT/cad-bom" 2>/dev/null
cp -r "$HERMES_DIR/workspace/notes" "$SNAPSHOT/notes" 2>/dev/null
cp -r "$HERMES_DIR/workspace/.learnings" "$SNAPSHOT/.learnings" 2>/dev/null
cp -r "$HERMES_DIR/workspace/hermes-recovery" "$SNAPSHOT/hermes-recovery" 2>/dev/null

# Clean pycache
find "$SNAPSHOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 3. Prune old snapshots (>10)
COUNT=$(ls -d "$BACKUP_DIR"/20* 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$MAX_VERSIONS" ]; then
    TO_DELETE=$((COUNT - MAX_VERSIONS))
    for d in $(ls -d "$BACKUP_DIR"/20* 2>/dev/null | sort | head -n "$TO_DELETE"); do
        echo "Pruning: $d"
        rm -rf "$d"
    done
fi

# 4. Commit and push
cd "$REPO_DIR"
git add -A
git commit -m "auto-backup $TS" --allow-empty
git push 2>&1

echo "Backup $TS done. Snapshots: $(ls -d "$BACKUP_DIR"/20* 2>/dev/null | wc -l)/$MAX_VERSIONS"
