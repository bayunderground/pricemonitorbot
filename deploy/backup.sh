#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/pricemonitorbot"
DB_NAME="neondb"
KEEP_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

pg_dump "$DB_NAME" | gzip > "$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"

find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "Backup completed: backup_${TIMESTAMP}.sql.gz"
