# Massive API Troubleshooting Guide

## Issue: Getting 0 Contracts

If you're seeing `Retrieved 0 option contracts` for all symbols, here's how to diagnose:

### Step 1: Test API Connection

```bash
python scripts/test_massive_api.py
```

This will:
- Verify API key is set
- Test current options chain
- Show raw API response
- Help identify response format issues

### Step 2: Check Common Issues

#### Issue 1: API Endpoint Wrong

**Symptom**: API returns 200 OK but empty data

**Fix**: The endpoint might be different. Check Massive API docs and update in `services/massive_data_feed.py`:

```python
# Line ~201 - Current endpoint
endpoint = "v3/snapshot/options/{symbol}".format(symbol=symbol)

# Might need to be:
# endpoint = "v2/options/chain/{symbol}"
# endpoint = "options/{symbol}/chain"
# etc.
```

#### Issue 2: Response Format Different

**Symptom**: API returns data but we're not parsing it correctly

**Fix**: The response structure might be different. Check the test output and update parsing in `services/massive_data_feed.py` (lines ~214-240).

Common formats:
- `{'results': [...]}`
- `{'data': [...]}`
- `{'items': [...]}`
- `{'contracts': [...]}`
- Direct list: `[...]`

#### Issue 3: Authentication Issue

**Symptom**: API returns 401/403 errors

**Fix**: 
1. Verify API key in `.env`: `MASSIVE_API_KEY=your_key`
2. Check if key needs to be in header vs query param
3. Verify subscription tier includes options data

#### Issue 4: Historical Data Not Supported

**Symptom**: Current data works, historical returns 0

**Fix**: Some APIs don't support historical snapshots. You may need to:
- Use a different endpoint for historical data
- Use aggregates endpoint instead
- Collect data daily going forward

### Step 3: Enable Debug Logging

Add to your script or set environment variable:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or:

```bash
export LOG_LEVEL=DEBUG
python scripts/collect_options_data.py ...
```

### Step 4: Check API Documentation

1. Verify the correct endpoint for options chains
2. Check if historical snapshots are supported
3. Verify required parameters
4. Check rate limits

### Step 5: Manual API Test

Test the API directly:

```python
import requests

api_key = "your_key"
url = "https://api.massive.com/v3/snapshot/options/AAPL"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Expected Behavior

### Normal Operation:
- ✅ API returns 200 OK
- ✅ Response contains contracts array
- ✅ Contracts are normalized and stored
- ✅ Database shows contracts

### Current Issue:
- ⚠️ API returns 200 OK
- ❌ Response parsed but empty
- ❌ 0 contracts stored

## Next Steps

1. **Run test script**: `python scripts/test_massive_api.py`
2. **Check response format**: Look at raw API response
3. **Update endpoint/parsing**: Based on actual API format
4. **Re-test**: Verify contracts are returned

## Quick Fixes

### If API uses different endpoint:

Edit `services/massive_data_feed.py` line ~201:

```python
# Change from:
endpoint = "v3/snapshot/options/{symbol}".format(symbol=symbol)

# To (example):
endpoint = "v2/options/chain/{symbol}".format(symbol=symbol)
```

### If response format is different:

Edit `services/massive_data_feed.py` lines ~214-240 to match actual response structure.

### If authentication is different:

Edit `services/massive_data_feed.py` `__init__` method to use correct auth format.

---

**Status**: Run `test_massive_api.py` first to diagnose the exact issue!

