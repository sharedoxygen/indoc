#!/bin/bash
# Celery Cleanup Script
# Kills all orphaned Celery workers and cleans up stale processes
# Use before starting fresh or when workers are stuck

set -e

echo "🧹 Celery Cleanup Script"
echo "======================="
echo ""

# Kill all Celery workers
echo "1. Killing all Celery worker processes..."
pkill -f "celery.*worker" 2>/dev/null && echo "   ✅ Killed existing workers" || echo "   ℹ️  No workers running"

# Kill Celery beat
echo "2. Killing Celery beat scheduler..."
pkill -f "celery.*beat" 2>/dev/null && echo "   ✅ Killed beat scheduler" || echo "   ℹ️  No beat running"

# Remove PID files
echo "3. Removing stale PID files..."
rm -f /Users/Collins/iDo/Projects/indoc/tmp/celery_worker.pid
rm -f /Users/Collins/iDo/Projects/indoc/tmp/celery_beat.pid
echo "   ✅ PID files removed"

# Clear Celery queue (optional - use carefully!)
read -p "4. Clear Redis task queue? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    redis-cli -h localhost -p 6379 DEL celery 2>/dev/null && echo "   ✅ Queue cleared" || echo "   ⚠️  Redis not accessible"
else
    echo "   ⏭️  Queue not cleared"
fi

# Verify cleanup
echo ""
echo "5. Verifying cleanup..."
WORKERS=$(ps aux | grep "celery.*worker" | grep -v grep | wc -l | tr -d ' ')
echo "   Celery workers still running: $WORKERS"

if [ "$WORKERS" -eq "0" ]; then
    echo ""
    echo "✅ Cleanup complete! Ready for fresh start."
    echo ""
    echo "Next steps:"
    echo "  cd /path/to/indoc"
    echo "  make local-e2e"
else
    echo ""
    echo "⚠️  Warning: $WORKERS workers still running"
    echo "   Try: pkill -9 -f celery"
fi

