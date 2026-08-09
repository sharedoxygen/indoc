#!/bin/bash
# Log Rotation Script for inDoc
# Rotates logs older than 24 hours and keeps archives for specified days
# Usage: ./scripts/ops/rotate_logs.sh [days_to_keep]

set -e

DAYS_TO_KEEP="${1:-30}"  # Default: keep archives for 30 days
MIN_AGE_HOURS=24  # Minimum age before rotation (24 hours)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/tmp"
ARCHIVE_DIR="$LOG_DIR/archive"
DATE_STAMP=$(date +"%Y-%m-%d")

echo "🔄 inDoc Log Rotation"
echo "===================="
echo "Project: $PROJECT_ROOT"
echo "Log Dir: $LOG_DIR"
echo "Archive: $ARCHIVE_DIR"
echo "Keep: $DAYS_TO_KEEP days"
echo ""

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR"

# Function to rotate a log file
rotate_log() {
    local log_file="$1"
    local log_name=$(basename "$log_file")
    local file_size=$(stat -f%z "$log_file" 2>/dev/null || echo "0")
    
    # Skip if file is empty or very small (< 1KB)
    if [ "$file_size" -lt 1024 ]; then
        echo "⏭️  Skipping $log_name (too small: ${file_size}B)"
        return
    fi
    
    # Skip if file was modified within last 24 hours
    local mod_time=$(stat -f "%m" "$log_file")
    local current_time=$(date +%s)
    local age_hours=$(( ($current_time - $mod_time) / 3600 ))
    
    if [ $age_hours -lt $MIN_AGE_HOURS ]; then
        echo "⏭️  Skipping $log_name (modified ${age_hours}h ago, keep for 24h)"
        return
    fi
    
    echo "📦 Rotating $log_name ($(numfmt --to=iec-i --suffix=B $file_size 2>/dev/null || echo ${file_size}B))"
    
    # Copy to archive with timestamp
    cp "$log_file" "$ARCHIVE_DIR/${log_name}.$DATE_STAMP"
    
    # Compress the archived copy
    gzip -f "$ARCHIVE_DIR/${log_name}.$DATE_STAMP"
    
    # Truncate the original log file (keep it for append)
    > "$log_file"
    
    echo "   ✅ Archived to ${log_name}.$DATE_STAMP.gz"
}

# Rotate all log files
echo "📋 Scanning for log files..."
for log_file in "$LOG_DIR"/*.log "$LOG_DIR"/*.out; do
    if [ -f "$log_file" ]; then
        rotate_log "$log_file"
    fi
done

echo ""
echo "🗑️  Cleaning up old archives (older than $DAYS_TO_KEEP days)..."
echo "   Note: Active logs kept for minimum 24 hours before rotation"

# Delete archives older than specified days
find "$ARCHIVE_DIR" -name "*.gz" -type f -mtime +$DAYS_TO_KEEP -print -delete | while read file; do
    echo "   🗑️  Deleted: $(basename "$file")"
done

echo ""
echo "📊 Archive Summary:"
echo "   Files: $(find "$ARCHIVE_DIR" -name "*.gz" | wc -l | tr -d ' ')"
echo "   Size:  $(du -sh "$ARCHIVE_DIR" | cut -f1)"

echo ""
echo "✅ Log rotation complete!"

