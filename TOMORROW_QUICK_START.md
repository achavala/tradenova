# ⚡ Tomorrow Quick Start - One Page Reference

## 🕐 9:25 AM ET - Start Command

```bash
cd /Users/chavala/TradeNova
source venv/bin/activate
python run_daily.py --paper
```

**That's it. Everything else is automatic.**

---

## 📊 Monitor

**Dashboard**: `http://localhost:8502`  
**Logs**: `tail -f logs/tradenova_daily.log`

---

## ⏰ Automatic Timeline

- **8:00 AM** - Pre-market warmup (if running)
- **9:30 AM** - Trading starts automatically
- **3:50 PM** - Positions auto-flatten
- **4:05 PM** - Daily report generated

---

## 🚨 Emergency Stop

```bash
pkill -f "run_daily.py"
```

---

## ✅ Status

✅ All systems validated  
✅ Paper account connected  
✅ Ready for automated trading  

---

*Quick Start - Tomorrow Morning*

