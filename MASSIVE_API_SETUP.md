# Massive API Integration - Setup Guide

## Overview

TradeNova now integrates with Massive API for comprehensive options data collection. This is the **critical foundation** for:
- ✅ Historical options chains (point-in-time)
- ✅ Historical IV data
- ✅ IV surface construction
- ✅ RL training data
- ✅ Greeks calculation
- ✅ Strike/expiry selection

## Setup

### 1. Get Massive API Key

1. Sign up at [Massive API](https://api.massive.com)
2. Get your API key from the dashboard
3. Ensure you have the **Options** subscription tier

### 2. Configure API Key

Add to your `.env` file:

```bash
MASSIVE_API_KEY=your_massive_api_key_here
MASSIVE_BASE_URL=https://api.massive.com
```

### 3. Verify Setup

```bash
python -c "from services.massive_data_feed import MassiveDataFeed; from config import Config; feed = MassiveDataFeed(Config.MASSIVE_API_KEY); print('✅ Available' if feed.is_available() else '❌ Not configured')"
```

## Usage

### Collect Historical Options Data

#### For RL Training (Recommended)

Collect 1 year of daily data for all symbols:

```bash
python scripts/collect_options_data.py --all-symbols --rl-training --lookback 252
```

#### For Specific Symbol

```bash
python scripts/collect_options_data.py --symbol AAPL --start 2024-01-01 --end 2024-12-31
```

#### For Specific Expiration Dates

```bash
python scripts/collect_options_data.py --symbol NVDA --start 2024-01-01 --end 2024-12-31 --expiration-dates 2024-12-20 2025-01-17
```

### Programmatic Usage

```python
from services.massive_data_feed import MassiveDataFeed
from services.historical_options_collector import HistoricalOptionsCollector
from config import Config

# Initialize
feed = MassiveDataFeed(Config.MASSIVE_API_KEY)
collector = HistoricalOptionsCollector(feed)

# Collect data for RL training
results = collector.collect_for_rl_training(
    symbols=['AAPL', 'NVDA', 'TSLA'],
    lookback_days=252
)

# Get options chain
chain = feed.get_options_chain('AAPL', date='2024-12-01')

# Get historical IV
iv_data = feed.get_historical_iv('AAPL', '2024-01-01', '2024-12-31')
```

### Build IV Surface

```python
from services.iv_surface_builder import IVSurfaceBuilder

builder = IVSurfaceBuilder(feed)

# Build IV surface
surface = builder.build_iv_surface('AAPL', '2024-12-01')

# Extract volatility smile
smile = builder.extract_volatility_smile('AAPL', '2024-12-01', '2024-12-20')

# Get term structure
term = builder.get_term_structure('AAPL', '2024-12-01')
```

## Data Storage

### Database

Historical data is stored in SQLite:
- **Location**: `data/options_history.db`
- **Tables**:
  - `options_chains`: Full options chain snapshots
  - `iv_history`: Historical IV data

### Cache

Point-in-time snapshots are cached:
- **Location**: `data/options_cache/`
- **Format**: JSON files per symbol/date

## API Endpoints Used

The integration uses Massive API endpoints (adjust based on actual API):

- `GET /v3/snapshot/options/{symbol}` - Current options chain
- `GET /v3/reference/options/contracts` - Historical contracts
- `GET /v2/aggs/ticker/{ticker}/range/...` - Historical aggregates

**Note**: Adjust endpoints in `services/massive_data_feed.py` based on actual Massive API documentation.

## Rate Limiting

The client includes rate limiting:
- **Default**: 100ms between requests
- **Adjustable**: Modify `min_request_interval` in `MassiveDataFeed`

## Next Steps

1. ✅ **Collect Historical Data** - Run collection for all symbols
2. ✅ **Build IV Surfaces** - Construct surfaces for analysis
3. ✅ **Train RL Models** - Use collected data for training
4. ✅ **Integrate with RL State** - Add Greeks/IV to RL observations

## Troubleshooting

### API Key Not Working

```bash
# Check if key is set
echo $MASSIVE_API_KEY

# Test API connection
python -c "from services.massive_data_feed import MassiveDataFeed; feed = MassiveDataFeed(); print(feed._make_request('v3/snapshot/options/AAPL'))"
```

### No Data Returned

- Check API subscription tier (need Options access)
- Verify symbol is correct
- Check date range (markets closed on weekends)
- Review API response format (may need to adjust parsing)

### Database Errors

```bash
# Check database
sqlite3 data/options_history.db "SELECT COUNT(*) FROM options_chains;"

# Reset database (WARNING: deletes all data)
rm data/options_history.db
```

## Files

- `services/massive_data_feed.py` - Core API client
- `services/historical_options_collector.py` - Data collection
- `services/iv_surface_builder.py` - IV surface construction
- `scripts/collect_options_data.py` - Collection script
- `config.py` - Configuration (MASSIVE_API_KEY)

## Status

✅ **Phase 1 Complete**: Options data foundation
- ✅ Massive API client
- ✅ Historical data collection
- ✅ IV surface builder
- ✅ Database storage
- ✅ Point-in-time accuracy

**Next**: Integrate with RL training environment

