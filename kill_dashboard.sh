#!/bin/bash
# Quick script to kill any Streamlit dashboard on port 8502

echo "🔍 Checking for processes on port 8502..."

PID=$(lsof -ti :8502 2>/dev/null)

if [ -z "$PID" ]; then
    echo "✅ No process found on port 8502"
else
    echo "⚠️  Found process (PID: $PID), killing it..."
    kill -9 $PID 2>/dev/null
    sleep 1
    echo "✅ Process killed"
fi

# Also check for any other Streamlit processes
STREAMLIT_PIDS=$(ps aux | grep -i "streamlit.*dashboard" | grep -v grep | awk '{print $2}')

if [ ! -z "$STREAMLIT_PIDS" ]; then
    echo "⚠️  Found additional Streamlit processes, killing them..."
    echo "$STREAMLIT_PIDS" | xargs kill -9 2>/dev/null
    echo "✅ All Streamlit dashboard processes killed"
fi

echo "✅ Port 8502 is now free"

