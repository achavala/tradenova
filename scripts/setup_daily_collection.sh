#!/bin/bash
# Setup Daily Collection Scripts
# Configures daily IV history collection and calendar updates

echo "=========================================="
echo "TradeNova Daily Collection Setup"
echo "=========================================="
echo ""

# Check if running on macOS (launchd) or Linux (cron)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS - Setting up launchd job"
    echo ""
    
    # Create launchd plist
    PLIST_FILE="$HOME/Library/LaunchAgents/com.tradenova.dailycollection.plist"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tradenova.dailycollection</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$PROJECT_DIR/scripts/collect_iv_history.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/daily_collection.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/daily_collection_error.log</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF
    
    echo "✅ Created launchd plist: $PLIST_FILE"
    echo ""
    echo "To enable daily collection:"
    echo "  launchctl load $PLIST_FILE"
    echo ""
    echo "To disable:"
    echo "  launchctl unload $PLIST_FILE"
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux - Setting up cron job"
    echo ""
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    CRON_JOB="0 20 * * * cd $PROJECT_DIR && /usr/bin/python3 $PROJECT_DIR/scripts/collect_iv_history.py >> $PROJECT_DIR/logs/daily_collection.log 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "collect_iv_history.py"; then
        echo "⚠️  Cron job already exists"
    else
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✅ Added cron job for daily IV collection (8:00 PM daily)"
    fi
    
    echo ""
    echo "Current crontab:"
    crontab -l | grep -A 1 "collect_iv_history"
    
else
    echo "⚠️  Unsupported OS: $OSTYPE"
    echo "   Please set up daily collection manually"
    echo ""
    echo "   Run daily:"
    echo "   python scripts/collect_iv_history.py"
    echo "   python scripts/update_calendars.py"
fi

echo ""
echo "=========================================="
echo "Setup Complete"
echo "=========================================="




