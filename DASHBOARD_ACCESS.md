# Dashboard Access Information

## 🌐 Dashboard URLs

### Fly.io Deployment (Production)
**Primary URL:** https://tradenova.fly.dev

**Alternative (if app name differs):**
- Check with: `flyctl apps list`
- Or: `flyctl status` (if in app directory)

### Local Development
**URL:** http://localhost:8501

To run locally:
```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
streamlit run dashboard.py
```

## 📱 Mobile Access
The Fly.io dashboard is accessible from any device with internet connection.

## 🔐 Access Requirements
- No authentication required (public dashboard)
- Real-time updates every 30 seconds (configurable in sidebar)

## 📊 Dashboard Features
- **Trade History** - View all executed trades
- **P&L Tracking** - Real-time profit/loss
- **System Logs** - Trading activity and decisions
- **Real-time Status** - Account, positions, risk level
- **Risk Metrics** - IV Rank, UVaR, Greeks

## 🚀 Quick Access Commands

### Check Fly.io Status
```bash
flyctl status
```

### View Dashboard Logs
```bash
flyctl logs
```

### Restart Dashboard
```bash
flyctl apps restart tradenova
```

## 🔧 Troubleshooting

If dashboard is not accessible:
1. Check Fly.io status: `flyctl status`
2. Check if app is running: `flyctl apps list`
3. View logs: `flyctl logs`
4. Restart if needed: `flyctl apps restart tradenova`

