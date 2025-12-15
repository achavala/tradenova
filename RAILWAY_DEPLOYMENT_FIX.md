# Railway Deployment Fix - Streamlit App

## ❌ Problem
Railway was trying to run `uvicorn main:app` (FastAPI) instead of Streamlit, causing:
```
ERROR: Error loading ASGI app. Attribute "app" not found in module "main".
```

## ✅ Solution

### Option 1: Use Procfile (Recommended)
The `Procfile` is already configured correctly:
```
web: streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

Railway should automatically detect and use the Procfile.

### Option 2: Manual Start Command in Railway Dashboard

If Railway still tries to use uvicorn:

1. Go to **Railway Dashboard** → Your Project
2. Click **Settings** → **Deploy**
3. Find **Start Command** field
4. Set it to:
   ```
   streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```
5. Click **Save**
6. Go to **Deployments** → Click **Redeploy**

## 🔍 Verify It's Working

After redeploy, check logs:
- ✅ Should see: "You can now view your Streamlit app"
- ✅ Should see: "Network URL: http://0.0.0.0:XXXX"
- ❌ Should NOT see: "Error loading ASGI app"

## 📱 Access on Mobile

Once deployed:
1. Copy the Railway URL (e.g., `https://tradenova-production.up.railway.app`)
2. Open on mobile browser
3. Bookmark for easy access

## 🛠️ Troubleshooting

### Still seeing uvicorn error?
1. Check Railway logs for the actual command being run
2. Verify Procfile is in root directory
3. Manually set Start Command in Railway dashboard
4. Redeploy

### Port issues?
- Railway automatically provides `$PORT` variable
- Streamlit will use it automatically
- No need to hardcode port numbers

### Dashboard not loading?
1. Check environment variables are set (ALPACA_API_KEY, etc.)
2. Check logs for errors
3. Verify Streamlit is installed in requirements.txt

---

**The Procfile is correct - Railway should use it automatically!**

