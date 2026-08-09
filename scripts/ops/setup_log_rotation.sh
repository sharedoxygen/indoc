#!/bin/bash
# Setup automatic log rotation via cron
# Runs daily at 2 AM
# Active logs kept for 24 hours minimum, archives kept for 30 days

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROTATE_SCRIPT="$PROJECT_ROOT/scripts/ops/rotate_logs.sh"

echo "📅 Setting up automatic log rotation for inDoc"
echo "=============================================="
echo ""

# Check if rotate script exists
if [ ! -f "$ROTATE_SCRIPT" ]; then
    echo "❌ Error: rotate_logs.sh not found at $ROTATE_SCRIPT"
    exit 1
fi

# Make sure it's executable
chmod +x "$ROTATE_SCRIPT"

# Cron job entry (runs daily at 2 AM)
CRON_ENTRY="0 2 * * * cd $PROJECT_ROOT && ./scripts/ops/rotate_logs.sh 30 >> /tmp/indoc_log_rotation.log 2>&1"

echo "Cron entry to be added:"
echo "  $CRON_ENTRY"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "rotate_logs.sh"; then
    echo "⚠️  Log rotation cron job already exists"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "rotate_logs"
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 1
    fi
    
    # Remove existing entry
    crontab -l | grep -v "rotate_logs.sh" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "📋 Current cron schedule:"
crontab -l | grep "rotate_logs" || echo "   (none)"
echo ""
echo "📝 Manual rotation:"
echo "   $ROTATE_SCRIPT [days_to_keep]"
echo ""
echo "📊 View rotation log:"
echo "   tail -f /tmp/indoc_log_rotation.log"
echo ""
echo "✅ Setup complete!"

