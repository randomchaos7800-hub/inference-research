#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/mnt/jellyfin-backups/forgejo"
DATE="$(date +%Y-%m-%d)"
ARCHIVE="$BACKUP_DIR/forgejo-backup-${DATE}.tar.gz"
STAGE="$(mktemp -d)"

cleanup() {
    rm -rf "$STAGE"
}
trap cleanup EXIT

mkdir -p "$BACKUP_DIR"

cp -a /etc/forgejo "$STAGE/etc-forgejo"
cp -a /var/lib/forgejo "$STAGE/var-lib-forgejo"

tar czf "$ARCHIVE" -C "$STAGE" .

find "$BACKUP_DIR" -name "forgejo-backup-*.tar.gz" -mtime +30 -delete 2>/dev/null || true

FILE_COUNT="$(tar -tzf "$ARCHIVE" 2>/dev/null | wc -l)"
if [ "$FILE_COUNT" -gt 0 ]; then
    echo "Integrity: OK (${FILE_COUNT} files)"
else
    echo "WARNING: Archive empty or corrupt: $ARCHIVE" >&2
fi

SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "Forgejo backup complete: $ARCHIVE ($SIZE)"
