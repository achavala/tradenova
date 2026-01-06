# Fly.io Deployment Guide for TradeNova

This guide will help you deploy TradeNova to Fly.io with automatic trading that starts at market open.

## Prerequisites

1. **Fly.io Account**: Sign up at [fly.io](https://fly.io)
2. **Fly CLI**: Install the Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
3. **Environment Variables**: Have your Alpaca API credentials ready

---

## Step 1: Login to Fly.io

```bash
fly auth login
```

---

## Step 2: Create Fly.io App

```bash
fly apps create tradenova
```

This creates a new app called "tradenova" (or choose your own name).

---

## Step 3: Set Environment Variables (Secrets)

Set all required environment variables as Fly.io secrets:

```bash
# Alpaca API credentials
fly secrets set ALPACA_API_KEY=your_api_key_here
fly secrets set ALPACA_SECRET_KEY=your_secret_key_here
fly secrets set ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Trading configuration
fly secrets set INITIAL_BALANCE=10000
fly secrets set MAX_ACTIVE_TRADES=10
fly secrets set POSITION_SIZE_PCT=0.50
fly secrets set STOP_LOSS_PCT=0.15

# Logging
fly secrets set LOG_LEVEL=INFO

# Timezone (for market hours)
fly secrets set TZ=America/New_York
```

**Important**: Replace `your_api_key_here` and `your_secret_key_here` with your actual Alpaca credentials.

---

## Step 4: Deploy to Fly.io

```bash
fly deploy
```

This will:
1. Build the Docker image
2. Push it to Fly.io
3. Deploy both processes (dashboard and trading system)

---

## Step 5: Verify Deployment

### Check App Status

```bash
fly status
```

### Check Logs

**Dashboard logs:**
```bash
fly logs --app tradenova --process web
```

**Trading system logs:**
```bash
fly logs --app tradenova --process trading
```

### Access Dashboard

The dashboard will be available at:
```
https://tradenova.fly.dev
```

(Replace `tradenova` with your app name if different)

---

## Step 6: Verify Trading System is Running

The trading system should automatically:
- Start at 8:00 AM ET (pre-market warmup)
- Begin trading at 9:30 AM ET (market open)
- Run trading cycles every 5 minutes during market hours
- Flatten positions at 3:50 PM ET (before market close)
- Generate daily report at 4:05 PM ET

Check logs to verify:
```bash
fly logs --app tradenova --process trading | grep "MARKET OPEN"
```

---

## Configuration Details

### Processes

The `fly.toml` defines two processes:

1. **web**: Streamlit dashboard (runs continuously)
2. **trading**: Trading system (runs continuously, scheduled internally)

### Automatic Startup

The trading system uses Python's `schedule` library to:
- Run pre-market warmup at 8:00 AM ET
- Start trading at 9:30 AM ET (market open)
- Execute trading cycles every 5 minutes
- Flatten positions at 3:50 PM ET
- Generate reports at 4:05 PM ET

**No manual intervention needed** - the system runs 24/7 and automatically handles market hours.

---

## Monitoring

### View Real-Time Logs

```bash
# All logs
fly logs --app tradenova

# Trading system only
fly logs --app tradenova --process trading

# Dashboard only
fly logs --app tragenova --process web
```

### Check Machine Status

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
   fly logs --app tradenova --process trading
   ```

2. **Verify environment variables:**
   ```bash
   fly secrets list
   ```

3. **Restart the trading process:**
   ```bash
   fly machine restart <machine-id> --process trading
   ```

### Authentication Errors

If you see "unauthorized" errors:

1. **Verify secrets are set:**
   ```bash
   fly secrets list
   ```

2. **Update secrets if needed:**
   ```bash
   fly secrets set ALPACA_API_KEY=new_key
   fly secrets set ALPACA_SECRET_KEY=new_secret
   ```

3. **Restart the machine:**
   ```bash
   fly machine restart <machine-id>
   ```

### Dashboard Not Accessible

1. **Check if web process is running:**
   ```bash
   fly status
   ```

2. **Check web logs:**
   ```bash
   fly logs --app tradenova --process web
   ```

3. **Restart web process:**
   ```bash
   fly machine restart <machine-id> --process web
   ```

---

## Updating the Application

### Deploy Updates

```bash
fly deploy
```

### Update Environment Variables

```bash
fly secrets set VARIABLE_NAME=new_value
fly machine restart <machine-id>
```

### Scale Resources

Edit `fly.toml` to adjust CPU/memory, then:

```bash
fly deploy
```

---

## Automatic Restart on Failure

Fly.io automatically restarts machines on failure. The trading system is configured to:
- Auto-start machines
- Keep at least 1 machine running
- Restart on crashes

---

## Cost Optimization

### Current Configuration

- **Dashboard**: 1 shared CPU, 512 MB RAM (always running)
- **Trading**: 2 shared CPUs, 1024 MB RAM (always running)

### Optional: Scale Down After Hours

You can configure auto-scaling in `fly.toml` to reduce costs after market hours, but for reliability, we recommend keeping machines running 24/7.

---

## Security Notes

1. **Never commit `.env` files** - Use Fly.io secrets instead
2. **API keys are stored securely** in Fly.io secrets
3. **HTTPS is enforced** for dashboard access
4. **Paper trading only** - No real money at risk

---

## Next Steps

1. ✅ Deploy to Fly.io
2. ✅ Verify trading system starts automatically
3. ✅ Monitor first trading day
4. ✅ Check dashboard for trade history
5. ✅ Review daily reports

---

## Support

- **Fly.io Docs**: https://fly.io/docs
- **Fly.io Status**: https://status.fly.io
- **TradeNova Logs**: `fly logs --app tradenova`

---

**Deployment Date**: December 15, 2025  
**Status**: Ready for automatic trading starting tomorrow at market open




