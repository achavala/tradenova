#!/bin/bash
#
# Stop Automatic Trading
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_FILE="$LAUNCHD_DIR/com.tradenova.trading.plist"

echo "🛑 Stopping Automatic Trading..."

if [ -f "$LAUNCHD_FILE" ]; then
    # Unload the job
    if launchctl list | grep -q "com.tradenova.trading"; then
        launchctl unload "$LAUNCHD_FILE" 2>/dev/null
        echo "✅ Unloaded launchd job"
    fi
    
    # Remove the file
    rm -f "$LAUNCHD_FILE"
    echo "✅ Removed plist file"
    echo ""
    echo "Automatic trading has been stopped."
else
    echo "⚠️  No automatic trading job found"
fi





