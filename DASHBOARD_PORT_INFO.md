# 📊 TradeNova Dashboard - Port Configuration

## Default Port Changed

**TradeNova Dashboard** now runs on **port 8502** by default to avoid conflicts with other applications.

---

## 🚀 Quick Start

### Recommended Method
```bash
./start_dashboard.sh
```

**Opens at**: `http://localhost:8502`

### Alternative Method
```bash
streamlit run dashboard.py
```

**Also opens at**: `http://localhost:8502` (configured in `.streamlit/config.toml`)

---

## 🔧 Port Configuration

### Current Configuration
- **Default Port**: `8502`
- **Config File**: `.streamlit/config.toml`
- **Reason**: Avoid conflict with other apps on port 8501

### Change Port (If Needed)

**Option 1: Command Line**
```bash
streamlit run dashboard.py --server.port 8503
```

**Option 2: Update Config**
Edit `.streamlit/config.toml`:
```toml
[server]
port = 8503  # Change to your preferred port
```

**Option 3: Use Launcher Script**
```bash
./run_dashboard.sh 8503
```

---

## 📍 URLs

### TradeNova Dashboard
- **Default**: `http://localhost:8502`
- **Custom**: `http://localhost:[YOUR_PORT]`

### Other Application
- **Your other app**: `http://localhost:8501` (unchanged)

---

## ✅ Verification

### Check Port in Use
```bash
# Check if port 8502 is available
lsof -i :8502

# Check if port 8501 is in use (your other app)
lsof -i :8501
```

### Test Dashboard
1. Run: `./start_dashboard.sh`
2. Open: `http://localhost:8502`
3. Verify: Browser tab shows "TradeNova - AI Trading Dashboard"

---

## 🎯 Quick Reference

### Start Dashboard
```bash
./start_dashboard.sh
```

### Custom Port
```bash
streamlit run dashboard.py --server.port 8503
```

### Stop Dashboard
```
CTRL + C (in terminal running dashboard)
```

---

**Status**: ✅ **Port 8502 Configured**

**No Conflicts**: ✅ **Port 8501 Available for Other Apps**

---

*Dashboard Port Configuration - Ready to Use*

