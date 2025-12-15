# Options Database - Persistence Guide

## ✅ Database Status: PERSISTENT

Your options data is stored in a **SQLite database on disk** - it will persist across reboots, system restarts, and even if you delete the code and reinstall.

## Database Location

**File**: `data/options_history.db`

**Full Path**: `/Users/chavala/TradeNova/data/options_history.db`

This is a standard SQLite database file that lives on your filesystem, just like any other file.

## Current Database Status

As of collection completion:

- **Size**: 624 MB (on disk)
- **Records**: 3,036,010 option contracts
- **Symbols**: 12 (NVDA, AAPL, TSLA, META, GOOG, MSFT, AMZN, MSTR, AVGO, PLTR, AMD, INTC)
- **Date Range**: 2024-12-01 to 2025-12-13
- **Unique Dates**: 254 trading days

## Persistence Guarantees

✅ **Survives reboots**: Database is on disk, not in memory  
✅ **Survives code changes**: Database file is separate from code  
✅ **Survives reinstalls**: As long as you don't delete the `data/` directory  
✅ **Backup-able**: Just copy the `.db` file to backup  
✅ **Portable**: SQLite databases work on any OS  

## Verify Database

### Quick Check

```bash
# Check if database exists
ls -lh data/options_history.db

# Verify data
python scripts/verify_options_database.py
```

### Query Database Directly

```bash
# Open SQLite shell
sqlite3 data/options_history.db

# Run queries
SELECT COUNT(*) FROM options_chains;
SELECT DISTINCT symbol FROM options_chains;
SELECT MIN(date), MAX(date) FROM options_chains;
.quit
```

## Database Schema

### `options_chains` Table

Stores full options chain snapshots:

```sql
- symbol: Stock ticker (TEXT)
- date: Snapshot date (TEXT, YYYY-MM-DD)
- expiration_date: Option expiration (TEXT)
- strike: Strike price (REAL)
- option_type: 'call' or 'put' (TEXT)
- bid, ask, last: Prices (REAL)
- volume, open_interest: Trading stats (INTEGER)
- implied_volatility: IV (REAL)
- delta, gamma, theta, vega: Greeks (REAL)
- underlying_price: Stock price (REAL)
```

### `iv_history` Table

Stores IV history (for time series analysis):

```sql
- symbol: Stock ticker
- date: Date
- expiration_date: Expiration
- strike: Strike price
- implied_volatility: IV value
- underlying_price: Stock price
```

## Backup Your Database

### Manual Backup

```bash
# Copy to backup location
cp data/options_history.db data/options_history.db.backup

# Or with timestamp
cp data/options_history.db "data/options_history_$(date +%Y%m%d).db"
```

### Automated Backup (Optional)

Add to your daily cron or script:

```bash
# Backup daily
cp data/options_history.db "data/backups/options_history_$(date +%Y%m%d).db"
```

## Restore Database

If you need to restore:

```bash
# Stop any running processes
# Copy backup back
cp data/options_history.db.backup data/options_history.db
```

## Database Maintenance

### Vacuum (Optimize)

SQLite databases can grow over time. To optimize:

```bash
sqlite3 data/options_history.db "VACUUM;"
```

### Check Integrity

```bash
sqlite3 data/options_history.db "PRAGMA integrity_check;"
```

## Accessing Data

### From Python

```python
from services.massive_data_feed import MassiveDataFeed
from config import Config

feed = MassiveDataFeed(Config.MASSIVE_API_KEY)

# Get chain for specific date
chain = feed.get_options_chain('AAPL', date='2024-12-01')

# Data is automatically loaded from database if available
```

### Direct SQL Queries

```python
import sqlite3

conn = sqlite3.connect('data/options_history.db')
cursor = conn.cursor()

# Get all contracts for a symbol on a date
cursor.execute("""
    SELECT * FROM options_chains 
    WHERE symbol = 'AAPL' AND date = '2024-12-01'
""")
contracts = cursor.fetchall()
```

## Troubleshooting

### Database Not Found

```bash
# Check if data directory exists
ls -la data/

# If missing, create it
mkdir -p data
```

### Database Corrupted

```bash
# Check integrity
sqlite3 data/options_history.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
```

### Database Too Large

```bash
# Vacuum to optimize
sqlite3 data/options_history.db "VACUUM;"

# Or rebuild from scratch (data will be lost)
rm data/options_history.db
# Re-run collection
```

## Summary

✅ **Your data is safe and persistent**  
✅ **Database: 624 MB, 3M+ records**  
✅ **Location: `data/options_history.db`**  
✅ **Survives reboots and reinstalls**  
✅ **Backup-able and portable**  

The database is working correctly and will persist across all system restarts!

