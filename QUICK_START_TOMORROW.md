# 🚀 Quick Start Guide - Tomorrow's Paper Trading

## Fast Reference for First Live Paper Trading Day

---

## ⏰ Timeline

### 8:00 AM - Pre-Market Setup
```bash
bash daily_checklist.sh
python test_paper_connection.py
./start_dashboard.sh  # Terminal 1 (or: streamlit run dashboard.py)
```

**Dashboard URL**: `http://localhost:8502`

### 9:28 AM - Start Trading System
```bash
python run_daily.py --paper  # Terminal 2
```

### 9:30 AM - Market Opens
- Monitor dashboard
- Watch logs: `tail -f logs/tradenova_daily.log`

### 3:50 PM - Market Close
- System auto-flattens positions
- Review daily report

### 4:05 PM - After-Market Review
```bash
cat logs/daily_report_$(date +%Y-%m-%d).txt
```

---

## 🔍 Quick Checks

### Before Starting
- [ ] `bash daily_checklist.sh` - All green
- [ ] `python test_paper_connection.py` - Connection OK
- [ ] Dashboard loads without errors
- [ ] Paper mode confirmed: `--paper` flag

### During Trading
- [ ] Dashboard shows activity
- [ ] Logs show no errors
- [ ] Risk level stays "normal"
- [ ] No excessive trading

### End of Day
- [ ] Positions auto-flattened
- [ ] Daily report generated
- [ ] No errors in logs
- [ ] Fill out `WEEK1_3_REPORT_TEMPLATE.md`

---

## 🚨 Emergency

**Stop Trading**:
```
CTRL + C  # In Terminal 2
```

**Check Positions**:
```bash
python -c "from alpaca_client import AlpacaClient; from config import Config; client = AlpacaClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets'); print('Positions:', len(client.get_positions()))"
```

---

## 📊 What to Watch

### Dashboard
- Equity curve
- RL confidence
- Ensemble agreement
- Active positions
- Risk level

### Logs
- Trade executions
- Risk triggers
- Errors/warnings
- News filter blocks

---

## ✅ Success Criteria

- ✅ No system errors
- ✅ Signals stable
- ✅ Fill rates >90%
- ✅ Win rate >50%
- ✅ Risk level normal
- ✅ Positions auto-flatten

---

**Full Checklist**: See `TOMORROW_CHECKLIST.md`

**Status**: ✅ **READY FOR TOMORROW**

