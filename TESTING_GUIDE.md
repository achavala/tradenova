# Testing Guide - How to Test Your Code

## ✅ Fixed Issue

The issue was a missing `List` import in `options_broker_client.py`. It's now fixed and all imports work!

---

## 🧪 How to Test Python Code

### Option 1: Use Python Interactive Mode

```bash
# Activate virtual environment first
source venv/bin/activate

# Start Python interactive shell
python

# Then type your imports:
>>> from services.options_data_feed import OptionsDataFeed
>>> from services.iv_calculator import IVCalculator
>>> print("Success!")
```

### Option 2: Use Python with -c Flag

```bash
source venv/bin/activate
python -c "from services.options_data_feed import OptionsDataFeed; print('Success!')"
```

### Option 3: Create a Test Script (Recommended)

```bash
# Create test file
nano test_my_code.py

# Add your test code:
from services.options_data_feed import OptionsDataFeed
print("Success!")

# Run it
python test_my_code.py
```

### Option 4: Use the Test Script I Created

```bash
source venv/bin/activate
python test_options.py
```

---

## 🚫 What Doesn't Work

**Don't type Python code directly in the shell:**

```bash
# ❌ This won't work:
from services.options_data_feed import OptionsDataFeed

# ✅ Instead, use:
python -c "from services.options_data_feed import OptionsDataFeed"
# or
python
>>> from services.options_data_feed import OptionsDataFeed
```

---

## 📝 Quick Test Examples

### Test Options Infrastructure

```bash
source venv/bin/activate
python test_options.py
```

### Test Individual Components

```bash
# Test IV Calculator
python -c "from services.iv_calculator import IVCalculator; print('IV Calculator works!')"

# Test GEX Calculator
python -c "from services.gex_calculator import GEXCalculator; print('GEX Calculator works!')"

# Test Options Agent
python -c "from core.agents.options_agent import OptionsAgent; print('Options Agent works!')"
```

### Test with Alpaca (Requires Credentials)

```python
# Create test_alpaca.py
from alpaca_client import AlpacaClient
from config import Config
from services.options_data_feed import OptionsDataFeed

client = AlpacaClient(
    Config.ALPACA_API_KEY,
    Config.ALPACA_SECRET_KEY,
    Config.ALPACA_BASE_URL
)

options_feed = OptionsDataFeed(client)
chain = options_feed.get_options_chain("AAPL")
print(f"Found {len(chain)} option contracts")
```

---

## 🎯 Summary

- ✅ **Fixed**: Missing `List` import in `options_broker_client.py`
- ✅ **All imports working**: All options infrastructure components import successfully
- ✅ **Test script created**: `test_options.py` for easy testing

**To test, always use:**
- `python test_options.py` (for full test)
- `python -c "your code here"` (for quick tests)
- `python` then type code (for interactive testing)

**Never type Python code directly in zsh/bash!**

