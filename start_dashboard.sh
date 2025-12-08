#!/bin/bash
# Quick start script for TradeNova Dashboard
# Uses port 8502 by default to avoid conflicts

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Warning: venv directory not found"
fi

echo "🚀 Starting TradeNova Dashboard..."
echo ""
echo "📍 URL: http://localhost:8502"
echo "📊 Dashboard: TradeNova - AI Trading System"
echo ""
echo "Press CTRL+C to stop"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Error: streamlit not found"
    echo ""
    echo "Installing streamlit..."
    pip install streamlit
fi

# Force port 8502 - override any config
streamlit run dashboard.py --server.port 8502 --server.headless false

