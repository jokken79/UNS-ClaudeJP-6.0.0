#!/bin/sh
# PostgreSQL Backup Script

BACKUP_DIR="/backups"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-uns_admin}"
DB_NAME="${POSTGRES_DB:-uns_claudejp}"
BACKUP_TIME="${BACKUP_TIME:-02:00}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
RUN_ON_STARTUP="${RUN_ON_STARTUP:-true}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to create backup
backup_database() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup of $DB_NAME..."
  BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz"

  PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    | gzip > "$BACKUP_FILE"

  if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed: $BACKUP_FILE"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup failed"
    return 1
  fi
}

# Function to cleanup old backups
cleanup_old_backups() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up backups older than $RETENTION_DAYS days..."
  find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleanup completed"
}

# Run backup on startup if enabled
if [ "$RUN_ON_STARTUP" = "true" ]; then
  backup_database
  cleanup_old_backups
fi

# Setup cron for scheduled backups
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Setting up cron job for daily backup at $BACKUP_TIME..."
HOUR=$(echo "$BACKUP_TIME" | cut -d: -f1)
MINUTE=$(echo "$BACKUP_TIME" | cut -d: -f2)
CRON_JOB="$MINUTE $HOUR * * * /app/backup.sh >> $BACKUP_DIR/backup.log 2>&1"
echo "$CRON_JOB" | crontab - 2>/dev/null || true
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cron job configured: $CRON_JOB"

# Start cron daemon and keep service alive
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup scheduler..."
crond -f -l 0 2>&1 &
CROND_PID=$!
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cron daemon running (PID: $CROND_PID)"

# Keep container alive
while true; do
  sleep 3600
  cleanup_old_backups
done
