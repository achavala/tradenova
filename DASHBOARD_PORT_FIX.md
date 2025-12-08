# 🔧 Dashboard Port Fix - Force Port 8502

## Issue Fixed

**Problem**: Dashboard still opening on port 8501  
**Solution**: Force port 8502 with explicit command-line override

---

## ✅ Solution - Force Port 8502

### Method 1: Use Fix Script (Recommended)

```bash
./fix_dashboard_port.sh
```

**This script**:
1. ✅ Stops any existing dashboard processes
2. ✅ Activates virtual environment
3. ✅ Forces port 8502 explicitly
4. ✅ Starts dashboard on correct port

---

### Method 2: Manual Command (Guaranteed)

```bash
# Step 1: Activate venv
source venv/bin/activate

# Step 2: Kill any existing streamlit
pkill -f streamlit

# Step 3: Start with explicit port override
streamlit run dashboard.py --server.port 8502 --server.headless false
```

**This forces port 8502** regardless of config file.

---

### Method 3: Updated Start Script

```bash
./start_dashboard.sh
```

**Now includes**: `--server.port 8502` override

---

## 🔍 Verify Port

### Check What's Running
```bash
# Check port 8501
lsof -i :8501

# Check port 8502
lsof -i :8502
```

### Expected Results
- **Port 8501**: Your other website (or nothing)
- **Port 8502**: TradeNova Dashboard (Python/streamlit process)

---

## 🚨 If Still Opening on 8501

### Force Stop and Restart

```bash
# Kill all streamlit processes
pkill -f streamlit

# Wait a moment
sleep 2

# Start with explicit port
source venv/bin/activate
streamlit run dashboard.py --server.port 8502 --server.headless false
```

---

## 📋 Complete Fix Command

```bash
cd /Users/chavala/TradeNova
pkill -f streamlit
source venv/bin/activate
streamlit run dashboard.py --server.port 8502 --server.headless false
```

**Opens at**: `http://localhost:8502`

---

## ✅ Verification Steps

1. **Check processes**:
   ```bash
   lsof -i :8502
   ```
   Should show Python/streamlit

2. **Open browser**:
   ```
   http://localhost:8502
   ```
   Should show TradeNova dashboard

3. **Check browser tab**:
   Should show "TradeNova - AI Trading Dashboard"

---

## 🎯 Port Configuration Summary

| Port | Application | Status |
|------|-------------|--------|
| 8501 | Your Other Website | ✅ Separate |
| 8502 | **TradeNova Dashboard** | ✅ **FORCED** |

---

## 📝 For Tomorrow

### Terminal 1 (Dashboard)
```bash
cd /Users/chavala/TradeNova
pkill -f streamlit  # Clean start
source venv/bin/activate
streamlit run dashboard.py --server.port 8502 --server.headless false
```

### Terminal 2 (Trading)
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

---

**Status**: ✅ **PORT 8502 FORCED**

**Command**: Always use `--server.port 8502` to override config

---

*Dashboard Port Fix - Port 8502 Guaranteed*

