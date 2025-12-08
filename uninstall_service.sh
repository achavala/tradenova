#!/bin/bash
# Uninstall TradeNova service

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$LAUNCH_AGENTS_DIR/com.tradenova.plist"

echo "="*70
echo "UNINSTALLING TRADENOVA SERVICE"
echo "="*70
echo ""

if [ -f "$TARGET_PLIST" ]; then
    echo "🛑 Stopping service..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null
    
    echo "🗑️  Removing plist..."
    rm "$TARGET_PLIST"
    
    echo "✅ Service uninstalled"
else
    echo "⚠️  Service not found (may already be uninstalled)"
fi

echo "="*70

