# Railway Deployment Guide - TradeNova Dashboard

## 🚀 Quick Deploy to Railway

Deploy your TradeNova dashboard to Railway so you can access it from your mobile device!

---

## 📋 Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code should be on GitHub (already done ✅)
3. **Environment Variables**: You'll need your Alpaca API keys

---

## 🎯 Step-by-Step Deployment

### Step 1: Create New Project on Railway

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `achavala/tradenova` repository
5. Railway will automatically detect it's a Python project

### Step 2: Configure Environment Variables

In Railway dashboard, go to your project → **Variables** tab and add:

```
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
PORT=8502
```

**Important**: Railway automatically provides `PORT` variable, but we set a default just in case.

### Step 3: Deploy

1. Railway will automatically start building and deploying
2. Wait for deployment to complete (usually 2-3 minutes)
3. Once deployed, Railway will provide a public URL like:
   - `https://tradenova-production.up.railway.app`

### Step 4: Access on Mobile

1. **Copy the Railway URL** from your project dashboard
2. **Open on your mobile browser** (Safari, Chrome, etc.)
3. **Bookmark it** for easy access
4. The dashboard is now accessible from anywhere! 📱

---

## 🔧 Configuration Files

The following files are already configured for Railway:

- ✅ `Procfile` - Tells Railway how to start the app
- ✅ `railway.json` - Railway-specific configuration
- ✅ `.streamlit/config.toml` - Streamlit server settings
- ✅ `requirements.txt` - Python dependencies

---

## 📱 Mobile Access Tips

### Bookmark on Mobile

**iOS (Safari)**:
1. Open the Railway URL
2. Tap the Share button
3. Select "Add to Home Screen"
4. Name it "TradeNova"

**Android (Chrome)**:
1. Open the Railway URL
2. Tap the menu (3 dots)
3. Select "Add to Home screen"
4. Name it "TradeNova"

### Mobile-Optimized Features

The dashboard is already mobile-friendly:
- ✅ Responsive layout
- ✅ Touch-friendly controls
- ✅ Sidebar navigation
- ✅ Charts scale to screen size

---

## 🔄 Updating Deployment

Whenever you push to GitHub:

1. Railway automatically detects changes
2. Triggers a new deployment
3. Your mobile app will show the latest version

**To manually trigger deployment:**
- Go to Railway dashboard → Your project → Deployments
- Click "Redeploy"

---

## 🛠️ Troubleshooting

### Dashboard Not Loading

1. **Check Railway logs**: Project → Deployments → View logs
2. **Verify environment variables**: Make sure Alpaca keys are set
3. **Check build status**: Ensure build completed successfully

### Can't Access from Mobile

1. **Verify URL**: Make sure you're using the Railway-provided URL
2. **Check network**: Try on WiFi and cellular data
3. **Clear cache**: Clear browser cache and reload

### Port Issues

Railway automatically assigns a port via `$PORT` environment variable. The Procfile handles this automatically.

---

## 🔐 Security Notes

- ✅ Your Alpaca API keys are stored securely in Railway (encrypted)
- ✅ Dashboard is publicly accessible (consider adding authentication if needed)
- ✅ Paper trading only - no real money at risk

---

## 📊 Monitoring

Railway provides:
- **Metrics**: CPU, Memory, Network usage
- **Logs**: Real-time application logs
- **Deployments**: History of all deployments

---

## 💰 Railway Pricing

- **Free Tier**: $5 credit/month (usually enough for dashboard)
- **Hobby Plan**: $5/month for more resources
- **Pro Plan**: $20/month for production workloads

For a dashboard, the free tier is usually sufficient!

---

## ✅ Deployment Checklist

- [ ] Railway account created
- [ ] Project created from GitHub repo
- [ ] Environment variables set (Alpaca keys)
- [ ] Deployment successful
- [ ] URL accessible from browser
- [ ] Mobile bookmark created
- [ ] Dashboard loads correctly

---

## 🎉 Success!

Once deployed, you can:
- ✅ Access dashboard from anywhere
- ✅ Monitor trades on mobile
- ✅ View trade history
- ✅ Check system status
- ✅ All from your phone! 📱

---

## 📞 Support

If you encounter issues:
1. Check Railway logs
2. Verify environment variables
3. Check GitHub for latest code
4. Railway support: [docs.railway.app](https://docs.railway.app)

---

**Happy Trading! 📈📱**


