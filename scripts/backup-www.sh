#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/mnt/jellyfin-backups/www"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

ARCHIVE="$BACKUP_DIR/www-backup-${DATE}.tar.gz"

tar czf "$ARCHIVE" \
  -C /home/dino \
  --ignore-failed-read \
  www/ \
  2>/dev/null || true

# Prune backups older than 30 days
find "$BACKUP_DIR" -name "www-backup-*.tar.gz" -mtime +30 -delete 2>/dev/null || true

FILE_COUNT=$(tar -tzf "$ARCHIVE" 2>/dev/null | wc -l)
if [ "$FILE_COUNT" -gt 0 ]; then
    echo "Integrity: OK (${FILE_COUNT} files)"
else
    echo "WARNING: Archive empty or corrupt: $ARCHIVE" >&2
fi

SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "www backup complete: $ARCHIVE ($SIZE)"
