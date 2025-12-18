# Quick Deploy to Fly.io - 5 Minutes

## Prerequisites

1. Install Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Login to Fly.io:
   ```bash
   fly auth login
   ```

---

## Step 1: Create App (30 seconds)

```bash
fly apps create tradenova
```

---

## Step 2: Set Secrets (2 minutes)

**Option A: Use script (recommended)**
```bash
./scripts/setup_fly_secrets.sh
```

**Option B: Manual setup**
```bash
fly secrets set ALPACA_API_KEY=your_key --app tradenova
fly secrets set ALPACA_SECRET_KEY=your_secret --app tradenova
fly secrets set ALPACA_BASE_URL=https://paper-api.alpaca.markets --app tradenova
fly secrets set LOG_LEVEL=INFO --app tradenova
```

---

## Step 3: Deploy (2 minutes)

**Option A: Use script (recommended)**
```bash
./scripts/deploy_to_fly.sh
```

**Option B: Manual deploy**
```bash
fly deploy
```

---

## Step 4: Verify (30 seconds)

```bash
# Check status
fly status

# Check logs
fly logs --app tradenova --process trading

# Access dashboard
open https://tradenova.fly.dev
```

---

## ✅ Done!

The trading system will automatically:
- ✅ Start at 8:00 AM ET (pre-market warmup)
- ✅ Begin trading at 9:30 AM ET (market open)
- ✅ Run trading cycles every 5 minutes
- ✅ Flatten positions at 3:50 PM ET
- ✅ Generate reports at 4:05 PM ET

**No manual intervention needed!**

---

## Troubleshooting

### Check if trading is running:
```bash
fly logs --app tradenova --process trading | grep "MARKET OPEN"
```

### Restart if needed:
```bash
fly machine restart <machine-id>
```

### View all logs:
```bash
fly logs --app tradenova
```

---

**That's it! Your system will trade automatically starting tomorrow at market open.**

