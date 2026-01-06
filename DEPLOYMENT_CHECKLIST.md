# Fly.io Deployment Checklist

Use this checklist to ensure successful deployment to Fly.io.

---

## Pre-Deployment

- [ ] Fly CLI installed (`fly version`)
- [ ] Logged in to Fly.io (`fly auth whoami`)
- [ ] Alpaca API credentials ready
- [ ] `.env` file exists with all required variables

---

## Deployment Steps

### 1. Create App
- [ ] Run: `fly apps create tradenova`
- [ ] Verify app created: `fly apps list`

### 2. Set Secrets
- [ ] Run: `./scripts/setup_fly_secrets.sh`
- [ ] OR manually set:
  - [ ] `ALPACA_API_KEY`
  - [ ] `ALPACA_SECRET_KEY`
  - [ ] `ALPACA_BASE_URL`
  - [ ] `LOG_LEVEL`
- [ ] Verify: `fly secrets list --app tradenova`

### 3. Deploy
- [ ] Run: `./scripts/deploy_to_fly.sh`
- [ ] OR manually: `fly deploy`
- [ ] Wait for build to complete
- [ ] Verify deployment success

### 4. Verify Deployment
- [ ] Check status: `fly status`
- [ ] Check logs: `fly logs --app tradenova`
- [ ] Access dashboard: `https://tradenova.fly.dev`
- [ ] Verify dashboard loads

---

## Post-Deployment Verification

### Trading System
- [ ] Check trading logs: `fly logs --app tradenova | grep "TRADING"`
- [ ] Verify trading system started
- [ ] Check for authentication errors
- [ ] Verify scheduler is running

### Dashboard
- [ ] Dashboard accessible via HTTPS
- [ ] Dashboard shows system status
- [ ] No errors in dashboard logs

### Automatic Trading
- [ ] Wait for 8:00 AM ET - check pre-market warmup
- [ ] Wait for 9:30 AM ET - check market open
- [ ] Verify trading cycles run every 5 minutes
- [ ] Check for executed trades

---

## Troubleshooting

### If Trading System Not Starting
- [ ] Check logs for errors
- [ ] Verify secrets are set correctly
- [ ] Check Python environment
- [ ] Restart machine: `fly machine restart <id>`

### If Dashboard Not Accessible
- [ ] Check if machine is running: `fly status`
- [ ] Check dashboard logs
- [ ] Verify port 8501 is exposed
- [ ] Check firewall/network settings

### If No Trades Executing
- [ ] Check authentication (no "unauthorized" errors)
- [ ] Verify market is open
- [ ] Check signal generation logs
- [ ] Verify risk management not blocking
- [ ] Check confidence thresholds

---

## Daily Monitoring

### Morning (Before Market Open)
- [ ] Check system is running: `fly status`
- [ ] Check logs for errors: `fly logs --app tradenova`
- [ ] Verify pre-market warmup at 8:00 AM ET

### During Market Hours
- [ ] Monitor trading logs
- [ ] Check for executed trades
- [ ] Verify signals are generated
- [ ] Check dashboard for updates

### After Market Close
- [ ] Verify positions flattened at 3:50 PM ET
- [ ] Check daily report generated at 4:05 PM ET
- [ ] Review daily performance
- [ ] Check for any errors

---

## Success Criteria

✅ **Deployment Successful When:**
- Dashboard accessible via HTTPS
- Trading system running continuously
- Pre-market warmup executes at 8:00 AM ET
- Trading starts at 9:30 AM ET
- Trading cycles run every 5 minutes
- Positions flattened at 3:50 PM ET
- Daily reports generated at 4:05 PM ET
- No authentication errors
- Trades execute when signals generated

---

## Next Steps After Deployment

1. **Monitor First Day**
   - Watch logs closely
   - Verify all scheduled tasks run
   - Check for any errors

2. **Verify Trades**
   - Check Alpaca dashboard for orders
   - Verify trades match signals
   - Review P&L

3. **Optimize**
   - Adjust thresholds if needed
   - Review signal quality
   - Tune risk parameters

---

**Deployment Date**: _______________  
**Verified By**: _______________  
**Status**: _______________




