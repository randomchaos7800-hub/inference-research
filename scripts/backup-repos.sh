#!/usr/bin/env bash
# Nightly git mirror backup to /mnt/jellyfin-backups/repos/
# Uses git clone --mirror on first run, git remote update on subsequent runs.
# Each repo becomes a bare .git mirror — can be re-cloned from it directly.
set -euo pipefail

BACKUP_DIR="/mnt/jellyfin-backups/repos"
mkdir -p "$BACKUP_DIR"

REPOS=(
    "/home/dino/frank"
    "/home/dino/.claude"
    "/home/dino/mike"
    "/home/dino/mesa-benchmark"
    "/home/dino/adam-selene"
    "/home/dino/.kato"
    "/home/dino/cj"
    "/home/dino/orchestra-release"
    "/home/dino/jubal"
    "/home/dino/dave-v2"
)

ERRORS=0
UPDATED=0
SKIPPED=0

for REPO in "${REPOS[@]}"; do
    NAME=$(basename "$REPO")
    MIRROR="$BACKUP_DIR/${NAME}.git"

    if [ ! -d "$REPO/.git" ]; then
        echo "[$NAME] skip — no .git"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    if [ -d "$MIRROR" ]; then
        if git -C "$MIRROR" remote update --prune 2>/dev/null; then
            echo "[$NAME] updated"
            UPDATED=$((UPDATED + 1))
        else
            echo "[$NAME] ERROR: remote update failed"
            ERRORS=$((ERRORS + 1))
        fi
    else
        if git clone --mirror "$REPO" "$MIRROR" 2>/dev/null; then
            echo "[$NAME] cloned"
            UPDATED=$((UPDATED + 1))
        else
            echo "[$NAME] ERROR: clone failed"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

echo "backup-repos: ${UPDATED} updated, ${SKIPPED} skipped, ${ERRORS} errors — $(date '+%Y-%m-%d %H:%M:%S')"
exit $ERRORS
