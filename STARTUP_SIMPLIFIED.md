# Simplified Startup Fix

## Issue
Machine was exiting immediately. The startup script was trying to run both dashboard and trading system, which may have been causing conflicts.

## Solution
**Simplified to start with dashboard only first**

### Changes Made

1. **start.sh** - Simplified to only start dashboard
   - Removed trading system startup (can be added later)
   - Dashboard is the main process (what Fly.io monitors)
   - Better logging for debugging

2. **Dockerfile** - Explicit bash command
   - Changed CMD to use explicit `/bin/bash`
   - Ensures bash is available

## Why This Works

- **Dashboard is the main process** - Fly.io monitors this
- **Simpler = more reliable** - Less can go wrong
- **Trading system can be added later** - Once dashboard is stable
- **Better error visibility** - Easier to debug

## Next Steps

1. **Deploy simplified version:**
   ```bash
   fly deploy --wait-timeout 300
   ```

2. **Verify dashboard starts:**
   ```bash
   fly logs --app tradenova
   fly status
   open https://tradenova.fly.dev
   ```

3. **Once dashboard is stable, add trading system:**
   - Can be done via separate process
   - Or add back to start.sh once dashboard is confirmed working

## Expected Result

- ✅ Dashboard starts successfully
- ✅ Accessible at https://tradenova.fly.dev
- ✅ No immediate exit
- ✅ Logs show dashboard startup

