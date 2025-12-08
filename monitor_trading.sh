#!/bin/bash
# Enhanced Monitoring Script for TradeNova
# Monitors logs for trades, errors, and warnings

LOG_FILE="logs/tradenova_daemon.log"

echo "="*70
echo "TRADENOVA TRADING MONITOR"
echo "="*70
echo ""
echo "Monitoring: $LOG_FILE"
echo ""
echo "Press Ctrl+C to stop"
echo "="*70
echo ""

# Function to show recent activity
show_recent() {
    echo "📊 RECENT ACTIVITY (last 20 lines):"
    tail -20 "$LOG_FILE" 2>/dev/null || echo "Log file not found"
    echo ""
}

# Function to show trades
show_trades() {
    echo "💰 TRADES EXECUTED:"
    grep -E "EXECUTING TRADE|Trade executed" "$LOG_FILE" 2>/dev/null | tail -10 || echo "No trades found"
    echo ""
}

# Function to show signals
show_signals() {
    echo "📈 SIGNALS GENERATED:"
    grep -E "Best signal selected|Signal evaluation" "$LOG_FILE" 2>/dev/null | tail -10 || echo "No signals found"
    echo ""
}

# Function to show errors/warnings
show_errors() {
    echo "⚠️  ERRORS & WARNINGS:"
    grep -Ei "(ERROR|WARN|data_unavailable|rejected|blocked)" "$LOG_FILE" 2>/dev/null | tail -10 || echo "No errors/warnings"
    echo ""
}

# Function to show scan summaries
show_scans() {
    echo "🔍 SCAN SUMMARIES:"
    grep -E "SCAN START|SCAN END" "$LOG_FILE" 2>/dev/null | tail -10 || echo "No scan data"
    echo ""
}

# Initial display
show_recent
show_trades
show_signals
show_errors
show_scans

# Watch mode
if [ "$1" == "--watch" ] || [ "$1" == "-w" ]; then
    echo "👀 WATCH MODE: Following log file..."
    echo "="*70
    tail -f "$LOG_FILE" 2>/dev/null | grep --line-buffered -E "(EXECUTING|signal|confidence|ERROR|WARN|SCAN|data_unavailable|rejected|blocked)" || echo "Log file not found or no matches"
else
    echo "💡 Tip: Run with --watch to follow log in real-time:"
    echo "   ./monitor_trading.sh --watch"
fi

