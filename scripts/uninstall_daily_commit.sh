#!/bin/bash
#
# Uninstall Daily Git Commit Automation
# Removes the macOS launchd job
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_FILE="$LAUNCHD_DIR/com.tradenova.dailycommit.plist"

echo "🗑️  Uninstalling Daily Git Commit Automation"
echo ""

# Check if job exists
if [ ! -f "$LAUNCHD_FILE" ]; then
    echo "⚠️  No installation found. Nothing to uninstall."
    exit 0
fi

# Unload the job
if launchctl list | grep -q "com.tradenova.dailycommit"; then
    echo "📦 Unloading launchd job..."
    launchctl unload "$LAUNCHD_FILE" 2>/dev/null || true
    echo "✅ Job unloaded"
else
    echo "⚠️  Job not currently loaded"
fi

# Remove plist file
if [ -f "$LAUNCHD_FILE" ]; then
    rm "$LAUNCHD_FILE"
    echo "✅ Removed plist file: $LAUNCHD_FILE"
fi

echo ""
echo "✅ Daily git commit automation uninstalled successfully!"

