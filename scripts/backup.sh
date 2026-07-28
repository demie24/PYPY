#!/bin/bash
# scripts/backup.sh
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/pypy_backup_$TIMESTAMP.tar.gz"

echo "===================================================="
echo "Starting PYPY Grid SaaS Backup utility..."
echo "===================================================="

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# 1. Dump PostgreSQL database using pg_dump
echo "Dumping PostgreSQL database logs..."
docker exec -t smart_grid_postgres pg_dump -U pypy_admin pypy_saas > "$BACKUP_DIR/pypy_db_$TIMESTAMP.sql" 2>/dev/null || {
    echo "Postgres container offline. Backing up SQLite files instead..."
    # Fallback to local SQLite if Postgres container is offline or during local tests
    if [ -f "./core/pypy.db" ]; then
        cp "./core/pypy.db" "$BACKUP_DIR/pypy_db_$TIMESTAMP.db"
    fi
}

# 2. Archive telemetry logs and backups database sql dumps
echo "Compiling system logs and configuration files..."
tar -czf "$BACKUP_PATH" -C "$BACKUP_DIR" .

# 3. Clean up raw SQL files
rm -f "$BACKUP_DIR/pypy_db_$TIMESTAMP.sql" "$BACKUP_DIR/pypy_db_$TIMESTAMP.db"

echo "===================================================="
echo "Backup complete!"
echo "Archive saved successfully at: $BACKUP_PATH"
echo "===================================================="
