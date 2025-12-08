#!/bin/bash
# Fix Dashboard Port - Force port 8502

echo "🔧 Fixing TradeNova Dashboard Port..."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Kill any existing streamlit processes
echo "1. Stopping any existing dashboard processes..."
pkill -f "streamlit.*dashboard" 2>/dev/null
pkill -f "streamlit.*8501" 2>/dev/null
sleep 2
echo "   ✅ Stopped"

# Activate venv
echo ""
echo "2. Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "   ✅ Virtual environment activated"
else
    echo "   ❌ Error: venv directory not found"
    exit 1
fi

# Verify streamlit
echo ""
echo "3. Verifying streamlit installation..."
if ! command -v streamlit &> /dev/null; then
    echo "   ⚠️  Streamlit not found, installing..."
    pip install streamlit --quiet
fi
echo "   ✅ Streamlit ready"

# Start dashboard on port 8502
echo ""
echo "4. Starting dashboard on port 8502..."
echo "   URL: http://localhost:8502"
echo ""
echo "   Press CTRL+C to stop"
echo ""

# Force port 8502 explicitly
streamlit run dashboard.py --server.port 8502 --server.headless false

