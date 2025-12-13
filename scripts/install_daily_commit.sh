#!/bin/bash
#
# Install Daily Git Commit Automation
# Sets up a macOS launchd job to commit and push changes daily at 6:00 PM
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PLIST_FILE="$SCRIPT_DIR/com.tradenova.dailycommit.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_FILE="$LAUNCHD_DIR/com.tradenova.dailycommit.plist"

echo "🚀 Installing Daily Git Commit Automation for TradeNova"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ ERROR: This script is designed for macOS only."
    echo "   For Linux, use cron instead: crontab -e"
    exit 1
fi

# Check if plist file exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "❌ ERROR: Plist file not found: $PLIST_FILE"
    exit 1
fi

# Check if commit script exists
COMMIT_SCRIPT="$SCRIPT_DIR/daily_git_commit.sh"
if [ ! -f "$COMMIT_SCRIPT" ]; then
    echo "❌ ERROR: Commit script not found: $COMMIT_SCRIPT"
    exit 1
fi

# Make commit script executable
chmod +x "$COMMIT_SCRIPT"
echo "✅ Made commit script executable"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCHD_DIR"
echo "✅ Created LaunchAgents directory"

# Update plist file with correct path
# Replace the hardcoded path with the actual project directory
sed "s|/Users/chavala/TradeNova|$PROJECT_DIR|g" "$PLIST_FILE" > "$LAUNCHD_FILE"
echo "✅ Created launchd plist file: $LAUNCHD_FILE"

# Unload existing job if it exists
if launchctl list | grep -q "com.tradenova.dailycommit"; then
    echo "⚠️  Unloading existing job..."
    launchctl unload "$LAUNCHD_FILE" 2>/dev/null || true
fi

# Load the job
echo "📦 Loading launchd job..."
if launchctl load "$LAUNCHD_FILE"; then
    echo "✅ Successfully installed daily git commit automation!"
    echo ""
    echo "📋 Configuration:"
    echo "   - Schedule: Daily at 6:00 PM"
    echo "   - Script: $COMMIT_SCRIPT"
    echo "   - Logs: $PROJECT_DIR/logs/git_auto_commit.log"
    echo ""
    echo "🔍 To check status:"
    echo "   launchctl list | grep tradenova"
    echo ""
    echo "🧪 To test manually:"
    echo "   $COMMIT_SCRIPT"
    echo ""
    echo "❌ To uninstall:"
    echo "   ./scripts/uninstall_daily_commit.sh"
    echo ""
else
    echo "❌ ERROR: Failed to load launchd job"
    exit 1
fi

