# 🚀 Quick Start: Automatic Trading Scheduler

**TradeNova will run automatically without interruption, always.**

---

## ✅ **Installation (Choose One)**

### **Option 1: macOS Service (Recommended)**
**Auto-starts on boot, auto-restarts on failure**

```bash
cd /Users/chavala/TradeNova
./install_service.sh
```

✅ **Done!** TradeNova will now:
- Start automatically when your Mac boots
- Restart automatically if it crashes
- Run continuously in background
- No terminal needed

---

### **Option 2: Forever Script**
**Keeps running, auto-restarts on failure**

```bash
cd /Users/chavala/TradeNova
./start_trading_forever.sh
```

✅ **Done!** TradeNova will:
- Run continuously
- Auto-restart on failure
- Log everything

**To stop:** Press `Ctrl+C` or `kill $(cat tradenova_forever.pid)`

---

### **Option 3: Direct Daemon**
**Run daemon directly**

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python tradenova_daemon.py --paper
```

---

## 📊 **Check Status**

```bash
# Check if running
ps aux | grep tradenova | grep -v grep

# Check service (if using Option 1)
launchctl list | grep com.tradenova

# View logs
tail -f logs/tradenova_daemon.log
```

---

## 🛑 **Stop Trading**

```bash
# If using macOS service
launchctl stop com.tradenova

# If using forever script
kill $(cat tradenova_forever.pid)

# If using daemon
kill $(cat tradenova_daemon.pid)
```

---

## 📝 **Full Documentation**

See `AUTOMATIC_SCHEDULER_SETUP.md` for complete details.

---

**Your trading scheduler is now set to run automatically!** ✅

