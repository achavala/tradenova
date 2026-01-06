# Railway Deployment Fix

## Problem
Railway was trying to run `uvicorn main:app` (FastAPI) instead of Streamlit.

## Solution
The `Procfile` explicitly tells Railway to use Streamlit.

## Configuration Files

### Procfile (Primary)
```
web: streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

### railway.json (Backup)
Also specifies the start command explicitly.

## Railway Settings

In Railway dashboard, make sure:
1. **Settings → Deploy → Start Command** is set to:
   ```
   streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```

2. **OR** Railway should automatically use the `Procfile`

## If Still Not Working

1. Go to Railway dashboard
2. Project → Settings → Deploy
3. Set **Start Command** manually to:
   ```
   streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```
4. Save and redeploy

## Verify

After deployment, check logs:
- Should see: "You can now view your Streamlit app"
- Should NOT see: "Error loading ASGI app"





