# 🚀 How to Start TradeNova Dashboard

## Quick Fix - Always Activate Venv First

The issue is that `streamlit` is installed in the virtual environment, so you need to activate it first.

---

## ✅ Correct Way to Start Dashboard

### Method 1: Activate Venv, Then Run (Recommended)

```bash
# Step 1: Activate virtual environment
source venv/bin/activate

# Step 2: Run dashboard
streamlit run dashboard.py --server.port 8502
```

**Opens at**: `http://localhost:8502`

---

### Method 2: Use Updated Script

```bash
./start_dashboard.sh
```

**Note**: Script now auto-activates venv, but if it doesn't work, use Method 1.

---

### Method 3: Python Module (Alternative)

```bash
source venv/bin/activate
python -m streamlit run dashboard.py --server.port 8502
```

---

## 🔍 Verify It's Working

### Check Streamlit is Available
```bash
source venv/bin/activate
which streamlit
streamlit --version
```

**Expected Output**:
```
/Users/chavala/TradeNova/venv/bin/streamlit
Streamlit, version 1.52.0
```

### Check Dashboard is Running
```bash
# After starting dashboard, check port
lsof -i :8502
```

**Expected**: Should show streamlit process

### Open in Browser
```
http://localhost:8502
```

**Expected**: TradeNova dashboard loads

---

## ⚠️ Common Issues

### Issue: "streamlit: command not found"

**Solution**: Activate venv first
```bash
source venv/bin/activate
```

### Issue: Port 8502 already in use

**Solution**: Use different port
```bash
source venv/bin/activate
streamlit run dashboard.py --server.port 8503
```

### Issue: Connection refused

**Solution**: 
1. Make sure venv is activated
2. Wait a few seconds for dashboard to start
3. Check if port is available: `lsof -i :8502`

---

## 📋 Step-by-Step for Tomorrow

### Pre-Market (8:15 AM)

**Terminal 1** (Dashboard):
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
streamlit run dashboard.py --server.port 8502
```

**Then open**: `http://localhost:8502`

**Terminal 2** (Trading System):
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

---

## ✅ Quick Test

```bash
# Test if it works
cd /Users/chavala/TradeNova
source venv/bin/activate
streamlit run dashboard.py --server.port 8502
```

**If successful**: Browser should open automatically, or go to `http://localhost:8502`

---

**Status**: ✅ **FIXED - Always activate venv first**

**Key**: `source venv/bin/activate` before running streamlit

---

*Dashboard Start Guide - Always Activate Venv First*

