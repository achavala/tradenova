# 🚀 Automatic Trading Scheduler Setup

**TradeNova will now run automatically without interruption, always.**

---

## ✅ **What's Been Set Up**

1. **Daemon Process** (`tradenova_daemon.py`)
   - Runs continuously in background
   - Auto-restarts on failure
   - Logs everything to files
   - Handles signals gracefully

2. **macOS Launch Agent** (`com.tradenova.plist`)
   - Starts automatically on boot
   - Restarts automatically on crash
   - Runs in background
   - Managed by macOS launchd

3. **Forever Script** (`start_trading_forever.sh`)
   - Simple script to keep trading running
   - Auto-restarts on failure
   - Can run manually or via cron

---

## 🎯 **Installation Options**

### **Option 1: macOS Launch Agent (Recommended - Auto-start on boot)**

This makes TradeNova start automatically when your Mac boots and restart if it crashes.

```bash
cd /Users/chavala/TradeNova
./install_service.sh
```

**What this does:**
- Installs TradeNova as a macOS service
- Starts automatically on boot
- Restarts automatically on failure
- Runs in background (no terminal needed)

**To manage:**
```bash
# Check status
launchctl list | grep com.tradenova

# Start manually
launchctl start com.tradenova

# Stop
launchctl stop com.tradenova

# Restart
launchctl unload ~/Library/LaunchAgents/com.tradenova.plist
launchctl load ~/Library/LaunchAgents/com.tradenova.plist

# View logs
tail -f logs/tradenova_service.log
tail -f logs/tradenova_service_error.log

# Uninstall
./uninstall_service.sh
```

---

### **Option 2: Forever Script (Simple - Manual start)**

Keeps TradeNova running and auto-restarts on failure.

```bash
cd /Users/chavala/TradeNova
./start_trading_forever.sh
```

**What this does:**
- Starts TradeNova
- Keeps it running
- Auto-restarts on failure
- Logs to `logs/tradenova_forever.log`

**To stop:**
- Press `Ctrl+C` in the terminal
- Or: `kill $(cat tradenova_forever.pid)`

---

### **Option 3: Daemon Script (Direct)**

Run the daemon directly:

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python tradenova_daemon.py --paper
```

**Options:**
- `--paper`: Use paper trading (default)
- `--dry-run`: Dry run mode (no real orders)
- `--daemon`: Fork to background

---

## 📊 **Monitoring**

### **Check if Running:**

```bash
# Check process
ps aux | grep tradenova

# Check service status (if using Launch Agent)
launchctl list | grep com.tradenova

# Check PID file
cat tradenova_daemon.pid
```

### **View Logs:**

```bash
# Main daemon log
tail -f logs/tradenova_daemon.log

# Error log
tail -f logs/tradenova_daemon_error.log

# Service log (Launch Agent)
tail -f logs/tradenova_service.log

# Service error log
tail -f logs/tradenova_service_error.log

# Trading activity
tail -f logs/tradenova_daily.log
```

---

## 🛡️ **Safety Features**

1. **Auto-Restart**: Restarts automatically on failure (up to 1000 times)
2. **Graceful Shutdown**: Handles SIGTERM/SIGINT properly
3. **Logging**: All activity logged to files
4. **PID Tracking**: Tracks process ID for management
5. **Error Recovery**: Waits 5 seconds before restart on error

---

## ⚙️ **Configuration**

### **Edit Service Settings:**

Edit `com.tradenova.plist` to change:
- Trading mode (paper/dry-run)
- Restart behavior
- Log locations
- Working directory

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.tradenova.plist
launchctl load ~/Library/LaunchAgents/com.tradenova.plist
```

---

## 🔧 **Troubleshooting**

### **Service Not Starting:**

1. Check logs:
   ```bash
   tail -f logs/tradenova_service_error.log
   ```

2. Verify paths in plist:
   ```bash
   cat ~/Library/LaunchAgents/com.tradenova.plist
   ```

3. Check permissions:
   ```bash
   chmod +x tradenova_daemon.py
   ```

### **Service Keeps Restarting:**

1. Check error log for the issue
2. Verify Alpaca API credentials
3. Check network connectivity
4. Review `logs/tradenova_daemon_error.log`

### **Stop Service:**

```bash
# If using Launch Agent
launchctl stop com.tradenova

# If using forever script
kill $(cat tradenova_forever.pid)

# If using daemon directly
kill $(cat tradenova_daemon.pid)
```

---

## ✅ **Verification**

After installation, verify it's running:

```bash
# Check if process exists
ps aux | grep tradenova | grep -v grep

# Check service status
launchctl list | grep com.tradenova

# Check logs for activity
tail -20 logs/tradenova_daemon.log
```

You should see:
- Process running
- Service loaded (if using Launch Agent)
- Log entries showing scheduler activity

---

## 🎉 **Summary**

**TradeNova will now:**
- ✅ Run automatically on boot (if using Launch Agent)
- ✅ Restart automatically on failure
- ✅ Run continuously without interruption
- ✅ Log everything for monitoring
- ✅ Handle errors gracefully

**No manual intervention needed!** 🚀

---

## 📝 **Quick Reference**

| Task | Command |
|------|---------|
| Install service | `./install_service.sh` |
| Uninstall service | `./uninstall_service.sh` |
| Start forever | `./start_trading_forever.sh` |
| Check status | `launchctl list \| grep com.tradenova` |
| View logs | `tail -f logs/tradenova_daemon.log` |
| Stop service | `launchctl stop com.tradenova` |

---

**Your trading scheduler is now set to run automatically without interruption!** ✅

