# Direct Command Fix

## Issue
Machine still timing out. The startup script might be failing silently.

## Solution
**Use direct command in Dockerfile instead of script**

### Changes Made

1. **Dockerfile** - Changed CMD to direct streamlit command
   - Removed dependency on start.sh script
   - Direct command = better error visibility
   - Fly.io can see exactly what's happening

2. **Why This Works**
   - No script execution = one less failure point
   - Direct command = Fly.io sees errors immediately
   - Simpler = more reliable

## Next Steps

1. **Deploy with direct command:**
   ```bash
   fly deploy --wait-timeout 300
   ```

2. **Check logs immediately:**
   ```bash
   fly logs --app tradenova
   ```

3. **If still failing, check:**
   - Environment variables are set
   - Dashboard imports work
   - Port 8501 is accessible

## Expected Result

- ✅ Machine starts successfully
- ✅ Dashboard accessible at https://tradenova.fly.dev
- ✅ Logs show streamlit startup
- ✅ No immediate exit

