# 📋 Tomorrow Morning Checklist

## Quick Reference for Market Open

---

## ⏰ Pre-Market (8:00-9:25 AM ET)

### 1. Clean Start
```bash
# Kill any orphan processes
pkill -f run_daily.py
pkill -f streamlit

# Verify clean
ps aux | grep -E "run_daily|streamlit" | grep -v grep
```

### 2. Start Dashboard (Terminal 1)
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
streamlit run dashboard.py --server.port 8502
```

**Open**: `http://localhost:8502`

**Verify**: System Status shows "Operational"

---

## ⏰ Market Open (9:25 AM ET)

### 3. Start Trading System (Terminal 2)
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

**Expected**: 
- `[INFO] Using PAPER trading account`
- `[INFO] Trading scheduler started`

---

## 📊 First 10-20 Minutes - What to Watch

### ✅ Good Signs:
- Few or zero trades (selective system)
- Clean logs (no errors)
- Stable confidence levels
- Dashboard shows operational status

### ⚠️ Watch For:
- Errors in logs
- Rapid signal flipping
- Dashboard errors
- Process crashes

---

## 🛑 Emergency Stop

```bash
pkill -f run_daily.py
```

---

## ✅ End of Day (3:50 PM ET)

**System will automatically**:
- Flatten all positions
- Generate daily report
- Save logs

**Review**:
```bash
cat logs/daily_report_$(date +%Y-%m-%d).txt
```

---

## 📝 Notes

- **Do NOT change code tonight** - System is stable
- **Quiet dashboard is GOOD** - System is selective
- **Monitor logs** - `tail -f logs/tradenova_daily.log`
- **Check dashboard** - System validation status

---

**Status**: ✅ **READY FOR TOMORROW**

*Tomorrow Morning Checklist - Quick Reference*



