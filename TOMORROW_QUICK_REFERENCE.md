# 🚀 Tomorrow's Quick Reference Card

## One-Page Operational Guide

---

## ⏰ Timeline

| Time | Action | Command |
|------|--------|---------|
| 8:00 AM | System check | `bash daily_checklist.sh` |
| 8:05 AM | Test connection | `python test_paper_connection.py` |
| 8:15 AM | Start dashboard | `./start_dashboard.sh` or `streamlit run dashboard.py` (Terminal 1) |
| 9:28 AM | Start trading | `./start_trading.sh --paper` (Terminal 2) |
| 9:30 AM | Market opens | Monitor dashboard & logs |
| 3:50 PM | Auto-flatten | System handles automatically |
| 4:10 PM | Review | `cat logs/daily_report_$(date +%Y-%m-%d).txt` |

---

## ✅ Pre-Market Checklist

```bash
# 1. System validation
bash daily_checklist.sh

# 2. Paper API test
python test_paper_connection.py

# 3. Start dashboard
streamlit run dashboard.py  # Terminal 1
```

**All must pass** ✅

---

## 🚀 Start Trading

### Option 1: Use Starter Script (Recommended - Auto-activates venv)

```bash
# Terminal 2
./start_trading.sh --paper
```

### Option 2: Manual (Must activate venv first)

```bash
# Terminal 2
source venv/bin/activate
python run_daily.py --paper
```

**⚠️ IMPORTANT: Always activate venv first if using Option 2!**

**Expected**: `[INFO] Using PAPER account`

---

## 📊 Monitor

**Dashboard**: Watch equity curve, confidence, risk level

**Logs**: `tail -f logs/tradenova_daily.log`

**Watch For**:
- ✅ Stable signals
- ✅ Normal risk level
- ✅ No errors
- ✅ Low activity (GOOD)

---

## 🛑 Emergency

**Stop**: `CTRL + C` (Terminal 2)

**Check Positions**:
```bash
python test_paper_connection.py
```

---

## ✅ Success = Stability

**Tomorrow is successful if**:
- ✅ No wild flips
- ✅ No errors
- ✅ Risk stays normal
- ✅ System stable
- ✅ Low activity (expected)

**Remember**: **Stability, not profits** (Week 1 goal)

---

## 📝 After Market

```bash
# Review report
cat logs/daily_report_$(date +%Y-%m-%d).txt

# Fill template
# Use: WEEK1_3_REPORT_TEMPLATE.md
```

---

**Full Guide**: `TOMORROW_CHECKLIST.md`  
**Status**: ✅ **READY**

