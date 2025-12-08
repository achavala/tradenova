# 🔧 Fix: ModuleNotFoundError - Virtual Environment Issue

## Issue

When running `python run_daily.py --paper`, you get:
```
ModuleNotFoundError: No module named 'pandas'
```

**Cause**: Virtual environment is not activated.

---

## ✅ Solution 1: Use Starter Script (Recommended)

**Use the new starter script that auto-activates venv:**

```bash
cd /Users/chavala/TradeNova
./start_trading.sh --paper
```

**This script**:
- ✅ Automatically activates virtual environment
- ✅ Checks for required packages
- ✅ Installs missing packages if needed
- ✅ Runs the trading system

---

## ✅ Solution 2: Manual Activation

**Always activate venv before running:**

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

**You should see `(venv)` in your terminal prompt** after activation.

---

## 🔍 Verify Virtual Environment

### Check if venv is activated:

```bash
# Should show venv path
which python
# Expected: /Users/chavala/TradeNova/venv/bin/python
```

### Check if pandas is installed:

```bash
source venv/bin/activate
python -c "import pandas; print(pandas.__version__)"
```

### Install missing packages:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📋 Quick Reference

### Start Trading (Auto-activates venv):
```bash
./start_trading.sh --paper
```

### Start Trading (Manual):
```bash
source venv/bin/activate
python run_daily.py --paper
```

### Check venv:
```bash
source venv/bin/activate
which python
```

---

## ✅ Status

**Fixed**: Starter script created that auto-activates venv

**Next**: Use `./start_trading.sh --paper` instead of direct python command

---

*Virtual Environment Issue Fixed*

