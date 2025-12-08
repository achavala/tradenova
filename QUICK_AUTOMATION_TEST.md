# ⚡ Quick Automation Test

## Validate Everything Works

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python validate_automation.py
```

**Expected**: All tests pass ✅

---

## Test Manual Start (Dry Run)

```bash
# Start in dry-run mode (no trades)
python run_daily.py --paper --dry-run
```

**Press Ctrl+C after a few seconds** to verify it starts correctly.

---

## Test Manual Start (Paper Trading)

```bash
# Start with paper trading
python run_daily.py --paper
```

**This will**:
- ✅ Connect to Alpaca paper account
- ✅ Start scheduler
- ✅ Wait for market open (9:30 AM)
- ✅ Run pre-market warmup (8:00 AM)
- ✅ Execute trading cycles every 5 minutes
- ✅ Flatten positions at 3:50 PM
- ✅ Generate report at 4:05 PM

**Press Ctrl+C to stop** (or let it run until market close)

---

## For Tomorrow Morning

### Option 1: Manual Start (Recommended First Day)

**At 9:25 AM ET:**

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

**Then monitor**:
- Dashboard: `http://localhost:8502`
- Logs: `tail -f logs/tradenova_daily.log`

---

### Option 2: Automated Start (After Validation)

**Set up launchd (macOS) or cron (Linux)** - see `AUTOMATION_SETUP.md`

---

## ✅ Pre-Flight Checklist

Before tomorrow:

- [ ] Run `validate_automation.py` - all tests pass
- [ ] Test manual start (dry-run): `python run_daily.py --paper --dry-run`
- [ ] Verify Alpaca paper account has funds
- [ ] Check dashboard: `http://localhost:8502`
- [ ] Review `AUTOMATION_SETUP.md` for automation options
- [ ] Set alarm for 9:25 AM (if manual start)

---

**Status**: Ready to test

**Next**: Run validation, then test manual start

---

*Quick Automation Test Guide*

