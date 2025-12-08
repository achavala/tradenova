#!/bin/bash
# Restart TradeNova Daemon with Latest Code
# This ensures the new option selector logic is loaded

set -e

echo "🔄 Restarting TradeNova Daemon..."
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Stop existing daemon processes
echo "1️⃣ Stopping existing daemon processes..."
pkill -f "tradenova_daemon.py" || echo "   (No existing daemon found)"
sleep 2

# Unload launch agent if it exists
if [ -f ~/Library/LaunchAgents/com.tradenova.plist ]; then
    echo "2️⃣ Unloading launch agent..."
    launchctl unload ~/Library/LaunchAgents/com.tradenova.plist 2>/dev/null || echo "   (Launch agent not loaded)"
    sleep 1
fi

# Load launch agent
if [ -f ~/Library/LaunchAgents/com.tradenova.plist ]; then
    echo "3️⃣ Loading launch agent with new code..."
    launchctl load ~/Library/LaunchAgents/com.tradenova.plist
    sleep 2
else
    echo "3️⃣ Launch agent not found, starting daemon directly..."
    nohup python3 "$PROJECT_ROOT/tradenova_daemon.py" > "$PROJECT_ROOT/logs/tradenova_daemon.log" 2>&1 &
    sleep 2
fi

# Verify daemon is running
if pgrep -f "tradenova_daemon.py" > /dev/null; then
    echo ""
    echo "✅ Daemon restarted successfully!"
    echo ""
    echo "📊 Monitor logs with:"
    echo "   tail -f logs/tradenova_daemon.log | grep -E 'SELECTED|REASONING|OPTION'"
    echo ""
    echo "🔍 Check daemon status:"
    echo "   ps aux | grep tradenova_daemon"
else
    echo ""
    echo "❌ Daemon failed to start. Check logs:"
    echo "   tail -20 logs/tradenova_daemon.log"
    exit 1
fi

