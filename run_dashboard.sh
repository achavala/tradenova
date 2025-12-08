#!/bin/bash
# Run TradeNova Dashboard with custom port
# Usage: ./run_dashboard.sh [port]
# Default port: 8502 (to avoid conflict with other apps on 8501)

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

PORT=${1:-8502}

echo "=========================================="
echo "Starting TradeNova Dashboard"
echo "Port: $PORT"
echo "URL: http://localhost:$PORT"
echo "=========================================="
echo ""
echo "Note: Using port $PORT to avoid conflict with other apps"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Error: streamlit not found"
    echo ""
    echo "Installing streamlit..."
    pip install streamlit
fi

streamlit run dashboard.py --server.port $PORT --server.headless true

