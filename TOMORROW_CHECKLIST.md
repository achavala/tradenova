# 🚀 Tomorrow's Live Paper Trading Checklist

## Complete Step-by-Step Operational Procedure

**Date**: [FILL IN DATE]  
**Mode**: PAPER TRADING  
**Status**: ✅ READY

---

## 🕖 PRE-MARKET (8:00-9:00 AM ET)

### Step 1: Run Automated Checklist (8:00 AM)

```bash
bash daily_checklist.sh
```

**Verify**:
- ✅ All imports successful
- ✅ Configuration valid
- ✅ Models found
- ✅ Directories ready
- ✅ No errors

**If any failure**: ❌ **DO NOT PROCEED** - Fix issues first

---

### Step 2: Test Alpaca Paper API Connection (8:05 AM)

```bash
python -c "from alpaca_client import AlpacaClient; from config import Config; client = AlpacaClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets'); print('✅ Paper API Connected:', client.get_account()['status'])"
```

**Expected**: `✅ Paper API Connected: ACTIVE`

**If fails**: Check API keys in `.env` file

---

### Step 3: Verify Paper Trading Mode (8:10 AM)

```bash
# Check that paper mode is default or explicit
grep -A 5 "paper" run_daily.py | head -10
```

**Verify**: Paper mode is properly configured

---

### Step 4: Start Streamlit Dashboard (8:15 AM)

**Terminal 1** (Keep open):
```bash
streamlit run dashboard.py
```

**Verify Dashboard**:
- ✅ Dashboard loads without errors
- ✅ No red error messages
- ✅ System Status shows "READY"
- ✅ Confidence indicators visible (should be neutral pre-market)
- ✅ RL model status shows "Loaded" (if model exists)

**If errors**: Check logs and fix before proceeding

---

### Step 5: Review Previous Day (If Applicable) (8:20 AM)

```bash
# Check if there's a previous day report
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
if [ -f "logs/daily_report_${YESTERDAY}.txt" ]; then
    echo "Previous day report found:"
    cat logs/daily_report_${YESTERDAY}.txt
else
    echo "No previous day report (first day)"
fi
```

---

### Step 6: Verify News Filter is Enabled (8:25 AM)

```bash
python -c "from core.live.news_filter import NewsFilter; nf = NewsFilter(); print('News Filter Status:', nf.get_status())"
```

**Verify**: News filter is active and configured

---

### Step 7: Final System Check (8:28 AM)

```bash
# Quick validation
python quick_validate.py
```

**All checks must pass**: ✅

---

## 🟧 MARKET OPEN PREPARATION (9:28-9:29 AM ET)

### Step 8: Start Trading System in PAPER MODE (9:28 AM)

**Terminal 2** (Keep open):
```bash
python run_daily.py --paper
```

**Expected Logs**:
```
[INFO] Using PAPER trading account
[INFO] Alpaca client initialized
[INFO] Pre-market warmup complete
[INFO] System ready for market open at 9:30 ET
[INFO] Risk Manager initialized
[INFO] Model Degrade Detector initialized
[INFO] News Filter initialized
```

**If errors appear**: Stop and investigate before 9:30 AM

---

### Step 9: Optional - Shadow Mode (9:29 AM)

**If you want to capture all signals**:

**Terminal 2** (Alternative):
```bash
python run_daily.py --paper --shadow --save-signals ./logs/signals_$(date +%Y%m%d).json
```

**This will**:
- ✅ Execute real paper trades
- ✅ Capture all internal decisions
- ✅ Store signals for analysis
- ✅ Great for Phase 4 backtesting

---

## 🟩 MARKET OPEN (9:30 AM ET)

### Step 10: Monitor First Signals (9:30-9:45 AM)

**Watch Dashboard For**:
- ✅ First signal evaluations appear
- ✅ Ensemble voting stability
- ✅ RL confidence (should not spike unless strong trend)
- ✅ No invalid orders
- ✅ Proper event filtering (no trades during news)
- ✅ No immediate flip-flopping

**Expected Behavior**:
- Signals may take a few minutes to generate
- Ensemble should show reasonable agreement (>50%)
- RL confidence should be moderate (0.5-0.8 range)
- No excessive trading

---

### Step 11: Ongoing Monitoring (9:30 AM - 3:50 PM)

**Dashboard Monitoring**:
- ✅ Equity curve updates
- ✅ RL confidence histogram
- ✅ Ensemble disagreement rates
- ✅ Active positions count
- ✅ Risk triggers
- ✅ Market volatility regime

**Log Monitoring** (Terminal 2):
```bash
# Watch logs in real-time
tail -f logs/tradenova_daily.log
```

**Watch For**:
- ⚠️ Warnings (investigate if frequent)
- ❌ Errors (stop if critical)
- 📊 Trade executions
- 🛡️ Risk manager triggers
- 🚫 News filter blocks

---

## ⛔ EMERGENCY PROCEDURES

### Kill Switch (If Needed)

**Option 1: Keyboard Interrupt**
```
CTRL + C (in Terminal 2)
```

**Option 2: Check for Emergency Script**
```bash
# If emergency_shutdown.py exists
python emergency_shutdown.py
```

**This Will**:
- ✅ Close all open positions (paper account)
- ✅ Cancel all pending orders
- ✅ Stop the system safely
- ✅ Generate emergency report

---

## 🟦 END OF DAY (3:50 PM ET)

### Step 12: System Auto-Flatten (3:50 PM)

**System Will Automatically**:
- ✅ Flatten all positions
- ✅ Stop new trades
- ✅ Generate daily report
- ✅ Flush logs

**Verify** (3:51 PM):
```bash
tail -n 30 logs/tradenova_daily.log
```

**Look For**:
```
[INFO] Flattening positions before market close
[INFO] Position closed: [SYMBOL]
[INFO] Daily flatten completed
[INFO] No open positions
```

---

### Step 13: Manual Verification (3:52 PM)

**Check Positions**:
```bash
# Verify no open positions
python -c "from alpaca_client import AlpacaClient; from config import Config; client = AlpacaClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets'); positions = client.get_positions(); print('Open positions:', len(positions))"
```

**Expected**: `Open positions: 0`

---

## 🟩 AFTER-MARKET REVIEW (4:05 PM ET)

### Step 14: Review Daily Report (4:05 PM)

```bash
cat logs/daily_report_$(date +%Y-%m-%d).txt
```

**Review**:
- ✅ Daily P&L
- ✅ Trade count
- ✅ Win rate
- ✅ Risk metrics
- ✅ Model performance

---

### Step 15: Dashboard Review (4:10 PM)

**Review Dashboard**:
- ✅ Equity curve (should show today's activity)
- ✅ Trade timestamps
- ✅ RL confidence distributions
- ✅ Ensemble agreement patterns
- ✅ Risk level throughout day

---

### Step 16: Log Review (4:15 PM)

```bash
# Review full day logs
less logs/tradenova_daily.log

# Search for errors
grep -i error logs/tradenova_daily.log

# Search for warnings
grep -i warning logs/tradenova_daily.log | tail -20
```

---

### Step 17: Signal Review (If Shadow Mode) (4:20 PM)

```bash
# Review captured signals
cat logs/signals_$(date +%Y%m%d).json | head -50

# Or load in Python for analysis
python -c "import json; data = json.load(open('logs/signals_$(date +%Y%m%d).json')); print(f'Total signals: {len(data)}')"
```

---

### Step 18: Fill Out Validation Report (4:30 PM)

**Use Template**: `WEEK1_3_REPORT_TEMPLATE.md`

**Document**:
- ✅ Daily P&L
- ✅ Trade count and win rate
- ✅ Signal patterns
- ✅ RL confidence
- ✅ Ensemble behavior
- ✅ Risk triggers
- ✅ Issues observed
- ✅ Key observations

---

## 📋 Pre-Trading Day Checklist

### Before Tomorrow Morning

- [ ] Alpaca Paper API keys active and tested
- [ ] `.env` file configured correctly
- [ ] Models available (grpo_final.zip or ppo_final.zip)
- [ ] All dependencies installed
- [ ] Logs directory exists
- [ ] Dashboard tested and working
- [ ] Paper trading mode verified
- [ ] News filter enabled
- [ ] Risk manager configured
- [ ] Emergency procedures understood

---

## 🚨 Red Flags - Stop Trading If:

- ❌ Daily loss limit hit
- ❌ Max drawdown exceeded
- ❌ Model degradation detected
- ❌ Frequent system errors
- ❌ Risk level shows "blocked"
- ❌ Excessive signal flipping
- ❌ Invalid orders being placed
- ❌ System instability

---

## ✅ Success Indicators

### System is Healthy When:
- ✅ Daily P&L is reasonable
- ✅ Win rate >50%
- ✅ Risk level stays "normal"
- ✅ No frequent errors
- ✅ Model confidence stable
- ✅ Ensemble agreement >60%
- ✅ Drawdowns controlled
- ✅ Fill rates >90%
- ✅ Slippage <0.1%

---

## 📞 Quick Reference

### Morning Routine
```bash
bash daily_checklist.sh
streamlit run dashboard.py  # Terminal 1
python run_daily.py --paper  # Terminal 2
```

### Monitoring
```bash
# Watch logs
tail -f logs/tradenova_daily.log

# Check dashboard
# (Already open in browser)
```

### End of Day
```bash
# Review report
cat logs/daily_report_$(date +%Y-%m-%d).txt

# Check positions
# (System auto-flattens at 3:50 PM)
```

---

## 🎯 Tomorrow's Goals

### Primary Goals
- ✅ System runs without errors
- ✅ Signals are stable
- ✅ No excessive trading
- ✅ Risk manager working
- ✅ News filter working
- ✅ Positions auto-flatten

### Data Collection Goals
- ✅ Capture all signals (if shadow mode)
- ✅ Document performance metrics
- ✅ Note any issues
- ✅ Record observations

---

## 📝 Notes Section

### Pre-Market Notes
- [ADD ANY PRE-MARKET OBSERVATIONS]

### During Market Notes
- [ADD ANY DURING-MARKET OBSERVATIONS]

### End of Day Notes
- [ADD ANY END-OF-DAY OBSERVATIONS]

### Issues Encountered
- [LIST ANY ISSUES]

### Key Learnings
- [LIST KEY LEARNINGS]

---

**Status**: ✅ **READY FOR TOMORROW**

**Next Action**: Follow this checklist step-by-step

**Remember**: This is PAPER TRADING - No real money at risk

---

*Complete Operational Checklist for First Live Paper Trading Day*

