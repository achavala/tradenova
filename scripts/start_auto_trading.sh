#!/bin/bash
#
# Start Automatic Trading - Runs daily at 9:00 AM ET
# This ensures the trading system is ready when market opens at 9:30 AM
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PLIST_FILE="$PROJECT_DIR/com.tradenova.trading.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_FILE="$LAUNCHD_DIR/com.tradenova.trading.plist"

echo "🚀 Setting up Automatic Trading for TradeNova"
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

# Check if venv exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "❌ ERROR: Virtual environment not found: $PROJECT_DIR/venv"
    echo "   Please run ./setup.sh first"
    exit 1
fi

# Make sure run_daily.py exists
if [ ! -f "$PROJECT_DIR/run_daily.py" ]; then
    echo "❌ ERROR: run_daily.py not found: $PROJECT_DIR/run_daily.py"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCHD_DIR"
echo "✅ Created LaunchAgents directory"

# Copy plist to LaunchAgents
cp "$PLIST_FILE" "$LAUNCHD_FILE"
echo "✅ Copied plist to LaunchAgents: $LAUNCHD_FILE"

# Unload existing job if it exists
if launchctl list | grep -q "com.tradenova.trading"; then
    echo "⚠️  Unloading existing job..."
    launchctl unload "$LAUNCHD_FILE" 2>/dev/null || true
fi

# Load the job
echo "📦 Loading launchd job..."
if launchctl load "$LAUNCHD_FILE"; then
    echo "✅ Successfully installed automatic trading!"
    echo ""
    echo "📋 Configuration:"
    echo "   - Schedule: Daily at 9:00 AM ET (30 min before market open)"
    echo "   - Script: $PROJECT_DIR/run_daily.py"
    echo "   - Mode: Paper Trading"
    echo "   - Logs: $PROJECT_DIR/logs/trading_automation.log"
    echo ""
    echo "📅 Trading Schedule:"
    echo "   9:00 AM - System starts"
    echo "   9:30 AM - Market opens, trading begins"
    echo "   3:50 PM - Flatten positions before close"
    echo "   4:05 PM - Generate daily report"
    echo ""
    echo "🔍 To check status:"
    echo "   launchctl list | grep tradenova"
    echo ""
    echo "🧪 To test manually (start now):"
    echo "   cd $PROJECT_DIR && source venv/bin/activate && python run_daily.py --paper"
    echo ""
    echo "❌ To uninstall:"
    echo "   ./scripts/stop_auto_trading.sh"
    echo ""
else
    echo "❌ ERROR: Failed to load launchd job"
    exit 1
fi





