#!/bin/bash
# Real-Time Signal Monitoring Script
# Shows why trades are/aren't executing

echo "🔍 TradeNova Signal Monitor"
echo "=========================="
echo ""
echo "Monitoring: logs/tradenova_daily.log"
echo "Press CTRL+C to stop"
echo ""
echo "=========================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

tail -f logs/tradenova_daily.log 2>/dev/null | while read line; do
    # Signal generation
    if echo "$line" | grep -qi "signal\|intent\|confidence"; then
        if echo "$line" | grep -qi "executing\|trade"; then
            echo -e "${GREEN}✅ $line${NC}"
        elif echo "$line" | grep -qi "too low\|blocked\|skip"; then
            echo -e "${YELLOW}⚠️  $line${NC}"
        else
            echo -e "${BLUE}ℹ️  $line${NC}"
        fi
    # Errors
    elif echo "$line" | grep -qi "error"; then
        echo -e "${RED}❌ $line${NC}"
    # Agent activity
    elif echo "$line" | grep -qi "agent\|orchestrator"; then
        echo -e "${BLUE}🤖 $line${NC}"
    # Filter activity
    elif echo "$line" | grep -qi "filter\|block\|news"; then
        echo -e "${YELLOW}🛡️  $line${NC}"
    # Status updates
    elif echo "$line" | grep -qi "status.*balance\|positions"; then
        echo -e "${GREEN}📊 $line${NC}"
    fi
done








