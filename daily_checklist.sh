#!/bin/bash
# TradeNova Daily Checklist Script
# Run this every trading day before market open

echo "=========================================="
echo "TRADENOVA DAILY CHECKLIST"
echo "Date: $(date +%Y-%m-%d)"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Quick Validation
echo "1. Running system validation..."
python quick_validate.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Validation passed${NC}"
else
    echo -e "${RED}❌ Validation failed - DO NOT START TRADING${NC}"
    exit 1
fi
echo ""

# Check 2: Previous day report
echo "2. Checking previous day report..."
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
if [ -f "logs/daily_report_${YESTERDAY}.txt" ]; then
    echo -e "${GREEN}✅ Previous day report found${NC}"
    echo "   Review: cat logs/daily_report_${YESTERDAY}.txt"
else
    echo -e "${YELLOW}⚠️  Previous day report not found${NC}"
fi
echo ""

# Check 3: Check for errors in logs
echo "3. Checking for recent errors..."
ERROR_COUNT=$(grep -i error logs/tradenova_daily.log 2>/dev/null | tail -10 | wc -l | tr -d ' ')
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $ERROR_COUNT recent errors${NC}"
    echo "   Review: tail -50 logs/tradenova_daily.log | grep -i error"
else
    echo -e "${GREEN}✅ No recent errors${NC}"
fi
echo ""

# Check 4: Check models
echo "4. Checking for trained models..."
if [ -f "models/grpo_final.zip" ] || [ -f "models/ppo_final.zip" ]; then
    echo -e "${GREEN}✅ Models found${NC}"
else
    echo -e "${YELLOW}⚠️  No models found${NC}"
    echo "   Train: python rl/train_rl.py --agent grpo --symbol SPY --timesteps 10000"
fi
echo ""

# Check 5: Market status (if market hours)
echo "5. Market status..."
HOUR=$(date +%H)
if [ "$HOUR" -ge 9 ] && [ "$HOUR" -lt 16 ]; then
    echo -e "${GREEN}✅ Market hours (9:30 AM - 4:00 PM ET)${NC}"
else
    echo -e "${YELLOW}ℹ️  Outside market hours${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "CHECKLIST COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review previous day report"
echo "  2. Start trading system:"
echo "     - Live: python run_daily.py"
echo "     - Paper: python run_daily.py --paper"
echo "     - Dry-run: python run_daily.py --dry-run"
echo "  3. Monitor dashboard: streamlit run dashboard.py"
echo ""
echo "For issues, see: OPERATIONAL_GUIDE.md"
echo ""

