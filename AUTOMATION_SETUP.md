# 🤖 TradeNova Automation Setup Guide

## Overview

This guide shows you how to set up TradeNova to start automatically at market open without manual intervention.

---

## ✅ Pre-Validation

**Before setting up automation, run the validation script:**

```bash
source venv/bin/activate
python validate_automation.py
```

**This validates**:
- ✅ Environment setup
- ✅ Configuration
- ✅ Alpaca connection
- ✅ Scheduler functionality
- ✅ Component initialization
- ✅ Automation readiness

---

## 🚀 Automation Options

### Option 1: Manual Start (Recommended for First Week)

**Start manually each morning:**

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

**Pros**:
- Full control
- Easy to monitor
- Can stop anytime

**Cons**:
- Requires manual intervention
- Must remember to start

---

### Option 2: macOS Launchd (Recommended for macOS)

**Create a Launch Agent that starts automatically:**

#### Step 1: Create Launch Agent File

```bash
nano ~/Library/LaunchAgents/com.tradenova.daily.plist
```

#### Step 2: Add Configuration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tradenova.daily</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/chavala/TradeNova/venv/bin/python</string>
        <string>/Users/chavala/TradeNova/run_daily.py</string>
        <string>--paper</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/chavala/TradeNova</string>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>25</integer>
        <key>Weekday</key>
        <integer>1</integer>  <!-- Monday = 1, Sunday = 0 -->
    </dict>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>25</integer>
        <key>Weekday</key>
        <integer>2</integer>  <!-- Tuesday -->
    </dict>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>25</integer>
        <key>Weekday</key>
        <integer>3</integer>  <!-- Wednesday -->
    </dict>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>25</integer>
        <key>Weekday</key>
        <integer>4</integer>  <!-- Thursday -->
    </dict>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>25</integer>
        <key>Weekday</key>
        <integer>5</integer>  <!-- Friday -->
    </dict>
    
    <key>StandardOutPath</key>
    <string>/Users/chavala/TradeNova/logs/launchd_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/chavala/TradeNova/logs/launchd_stderr.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

#### Step 3: Load Launch Agent

```bash
launchctl load ~/Library/LaunchAgents/com.tradenova.daily.plist
```

#### Step 4: Verify

```bash
launchctl list | grep tradenova
```

#### Step 5: Test (Optional)

```bash
# Start manually to test
launchctl start com.tradenova.daily

# Check logs
tail -f /Users/chavala/TradeNova/logs/launchd_stdout.log
```

#### Step 6: Unload (If Needed)

```bash
launchctl unload ~/Library/LaunchAgents/com.tradenova.daily.plist
```

**Note**: Launchd uses 24-hour format. 9:25 AM = Hour 9, Minute 25.

---

### Option 3: Cron Job (Linux/Mac)

**Add to crontab:**

```bash
crontab -e
```

**Add this line:**

```cron
# TradeNova - Start at 9:25 AM ET (market opens at 9:30 AM) on weekdays
25 9 * * 1-5 cd /Users/chavala/TradeNova && /Users/chavala/TradeNova/venv/bin/python run_daily.py --paper >> /Users/chavala/TradeNova/logs/cron.log 2>&1
```

**Note**: Adjust timezone if needed. Cron uses system timezone.

**Verify cron job:**

```bash
crontab -l
```

---

### Option 4: Systemd Service (Linux)

**Create service file:**

```bash
sudo nano /etc/systemd/system/tradenova.service
```

**Add configuration:**

```ini
[Unit]
Description=TradeNova Daily Trading Bot
After=network.target

[Service]
Type=simple
User=chavala
WorkingDirectory=/Users/chavala/TradeNova
ExecStart=/Users/chavala/TradeNova/venv/bin/python run_daily.py --paper
Restart=on-failure
StandardOutput=append:/Users/chavala/TradeNova/logs/systemd.log
StandardError=append:/Users/chavala/TradeNova/logs/systemd_error.log

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable tradenova.service
sudo systemctl start tradenova.service
```

**Check status:**

```bash
sudo systemctl status tradenova.service
```

---

## ⚠️ Important Notes

### Timezone Considerations

**All times are in your system timezone.**

- **Market Open**: 9:30 AM ET
- **Pre-Market Warmup**: 8:00 AM ET
- **Market Close Flatten**: 3:50 PM ET
- **Daily Report**: 4:05 PM ET

**If you're not in ET timezone**, adjust times accordingly:
- **PT (3 hours behind)**: Start at 6:25 AM PT
- **CT (1 hour behind)**: Start at 8:25 AM CT
- **MT (2 hours behind)**: Start at 7:25 AM MT

### Weekdays Only

**Markets are closed on weekends and holidays.**

The automation should only run Monday-Friday. Launchd and cron examples above include weekday filters.

### Process Management

**The script runs continuously** until:
- Market close (auto-stops)
- Manual stop (Ctrl+C)
- System shutdown

**For 24/7 operation**, use:
- Launchd (macOS) - auto-restarts on failure
- Systemd (Linux) - auto-restarts on failure
- Cron - runs once per day (script handles continuous operation)

---

## 🔍 Monitoring

### Check if Running

```bash
# Check process
ps aux | grep "run_daily.py"

# Check logs
tail -f logs/tradenova_daily.log

# Check dashboard
# Open http://localhost:8502
```

### Stop Running Instance

```bash
# Find process
ps aux | grep "run_daily.py"

# Kill process
pkill -f "run_daily.py"
```

---

## ✅ Validation Checklist

Before going fully automated:

- [ ] Run `validate_automation.py` - all tests pass
- [ ] Test manual start: `python run_daily.py --paper`
- [ ] Verify Alpaca paper account connection
- [ ] Check scheduler starts correctly
- [ ] Monitor first day manually
- [ ] Verify positions flatten at EOD
- [ ] Check daily report generation
- [ ] Set up automation (launchd/cron/systemd)
- [ ] Test automation start
- [ ] Monitor logs for first automated day

---

## 🚨 Emergency Stop

**If something goes wrong:**

1. **Stop the process:**
   ```bash
   pkill -f "run_daily.py"
   ```

2. **Unload automation (if using launchd):**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.tradenova.daily.plist
   ```

3. **Check logs:**
   ```bash
   tail -50 logs/tradenova_daily.log
   ```

4. **Flatten positions manually (if needed):**
   ```bash
   # Use Alpaca web interface or API
   ```

---

## 📋 Quick Reference

### Manual Start
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

### Validate Setup
```bash
python validate_automation.py
```

### Check Status
```bash
ps aux | grep "run_daily.py"
tail -f logs/tradenova_daily.log
```

### Stop Process
```bash
pkill -f "run_daily.py"
```

---

**Status**: Ready for automation setup

**Next**: Run `validate_automation.py` first, then choose automation method

---

*Automation Setup Guide - Choose Your Method*

