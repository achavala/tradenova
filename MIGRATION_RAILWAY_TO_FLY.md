# Migration Guide: Railway to Fly.io

This guide helps you migrate TradeNova from Railway to Fly.io for automatic trading.

---

## Why Migrate to Fly.io?

✅ **Better for long-running processes** - Trading system runs 24/7  
✅ **More reliable** - Automatic restarts and health checks  
✅ **Better resource management** - Separate processes for dashboard and trading  
✅ **Cost-effective** - Pay only for what you use  
✅ **Automatic scaling** - Handles traffic spikes automatically  

---

## Migration Steps

### Step 1: Install Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

### Step 2: Login to Fly.io

```bash
fly auth login
```

### Step 3: Create Fly.io App

```bash
fly apps create tradenova
```

### Step 4: Set Environment Variables

**Option A: Use script (recommended)**
```bash
./scripts/setup_fly_secrets.sh
```

**Option B: Manual setup**
```bash
# Get your secrets from Railway or .env file
fly secrets set ALPACA_API_KEY=your_key --app tradenova
fly secrets set ALPACA_SECRET_KEY=your_secret --app tradenova
fly secrets set ALPACA_BASE_URL=https://paper-api.alpaca.markets --app tradenova
fly secrets set LOG_LEVEL=INFO --app tradenova
```

### Step 5: Deploy

```bash
./scripts/deploy_to_fly.sh
```

Or manually:
```bash
fly deploy
```

### Step 6: Verify Deployment

```bash
# Check status
fly status

# Check logs
fly logs --app tradenova

# Access dashboard
open https://tradenova.fly.dev
```

---

## Key Differences

### Railway vs Fly.io

| Feature | Railway | Fly.io |
|---------|---------|--------|
| **Process Management** | Single process | Multiple processes supported |
| **Long-running Tasks** | Limited | Excellent |
| **Scheduling** | External (cron) | Internal (Python schedule) |
| **Health Checks** | Basic | Advanced |
| **Cost** | Per hour | Per machine hour |
| **Scaling** | Manual | Automatic |

---

## What Changed

### 1. Configuration Files

- ✅ `fly.toml` - Fly.io configuration (replaces `railway.json`)
- ✅ `Dockerfile` - Container definition (same as before)
- ✅ `start.sh` - Startup script for both processes

### 2. Process Management

**Railway**: Single process (dashboard only)  
**Fly.io**: Two processes (dashboard + trading system)

The `start.sh` script runs:
- Trading system in background (`run_daily.py`)
- Dashboard in foreground (Streamlit)

### 3. Environment Variables

**Railway**: Set in Railway dashboard  
**Fly.io**: Set via `fly secrets set` command

### 4. Automatic Trading

**Railway**: Required external cron/scheduler  
**Fly.io**: Built-in Python scheduler (no external dependencies)

---

## Automatic Trading Schedule

The trading system automatically runs:

| Time (ET) | Action |
|----------|--------|
| 8:00 AM | Pre-market warmup |
| 9:30 AM | Market open - start trading |
| Every 5 min | Trading cycle |
| 3:50 PM | Flatten positions |
| 4:05 PM | Daily report |

**No manual intervention needed!**

---

## Monitoring

### View Logs

```bash
# All logs
fly logs --app tradenova

# Filter for trading
fly logs --app tradenova | grep "TRADING"

# Filter for errors
fly logs --app tradenova | grep "ERROR"
```

### Check Status

```bash
fly status
fly machine list
```

### View Metrics

```bash
fly metrics
```

---

## Troubleshooting

### Trading System Not Starting

1. **Check logs:**
   ```bash
   fly logs --app tradenova
   ```

2. **Verify secrets:**
   ```bash
   fly secrets list --app tradenova
   ```

3. **Restart machine:**
   ```bash
   fly machine restart <machine-id>
   ```

### Dashboard Not Accessible

1. **Check if running:**
   ```bash
   fly status
   ```

2. **Check logs:**
   ```bash
   fly logs --app tradenova | grep "streamlit"
   ```

3. **Restart:**
   ```bash
   fly machine restart <machine-id>
   ```

---

## Cleanup Railway (Optional)

After verifying Fly.io is working:

1. **Stop Railway service:**
   - Go to Railway dashboard
   - Stop the service

2. **Delete Railway app (optional):**
   - Remove from Railway dashboard

---

## Rollback Plan

If you need to rollback to Railway:

1. **Keep Railway app running** until Fly.io is verified
2. **Monitor both** for a few days
3. **Switch traffic** once confident

---

## Next Steps

1. ✅ Deploy to Fly.io
2. ✅ Verify trading system starts automatically
3. ✅ Monitor first trading day
4. ✅ Check dashboard for trades
5. ✅ Review daily reports

---

## Support

- **Fly.io Docs**: https://fly.io/docs
- **Fly.io Status**: https://status.fly.io
- **TradeNova Logs**: `fly logs --app tradenova`

---

**Migration Date**: December 15, 2025  
**Status**: Ready for automatic trading on Fly.io

