# Option Symbol Format Fix

**Date:** December 19, 2025  
**Status:** ✅ **FIXED**

---

## 🔍 PROBLEM IDENTIFIED

### **Issue:**
- Option symbols were not in the correct format for Alpaca
- Expected format: `AAPL251219C00267500` (SYMBOL + YYMMDD + C/P + 8-digit strike)
- System was using raw symbols from API which might not match this format

### **Format Breakdown:**
```
AAPL251219C00267500
│    │     │ │
│    │     │ └─ Strike: 00267500 (8 digits, $267.50 * 1000)
│    │     └─── Type: C (Call) or P (Put)
│    └───────── Date: 251219 (Dec 19, 2025 - YYMMDD)
└─────────────── Symbol: AAPL
```

---

## ✅ SOLUTION IMPLEMENTED

### **1. Symbol Formatting Function**
- Constructs option symbol from contract details if not provided
- Validates existing symbols match expected format
- Reconstructs symbol if format is incorrect

### **2. Format Validation**
- Checks if symbol matches pattern: `^([A-Z]{1,5})(\d{6})([CP])(\d{8})$`
- Reconstructs from contract details if validation fails

### **3. Symbol Construction Logic**
```python
# Extract details
strike_price = float(contract.get('strike_price', 0))
contract_type = contract.get('type', 'call').lower()
expiration = target_expiration

# Format components
date_str = expiration.strftime('%y%m%d')  # YYMMDD
type_char = 'C' if contract_type == 'call' else 'P'
strike_int = int(strike_price * 1000)  # Convert to integer
strike_str = f'{strike_int:08d}'  # Pad to 8 digits

# Combine
option_symbol = f'{symbol}{date_str}{type_char}{strike_str}'
```

---

## 📋 CODE CHANGES

### **File:** `core/live/integrated_trader.py`

**Before:**
```python
option_symbol = option_contract.get('symbol') or option_contract.get('contract_symbol')
if not option_symbol:
    logger.warning("No option symbol found")
    return
```

**After:**
```python
option_symbol = option_contract.get('symbol') or option_contract.get('contract_symbol')

# If not provided, construct from contract details
if not option_symbol:
    strike_price = float(option_contract.get('strike_price', 0))
    contract_type = option_contract.get('type', 'call').lower()
    date_str = target_expiration.strftime('%y%m%d')
    type_char = 'C' if contract_type == 'call' else 'P'
    strike_int = int(strike_price * 1000)
    strike_str = f'{strike_int:08d}'
    option_symbol = f'{symbol}{date_str}{type_char}{strike_str}'

# Validate format
import re
pattern = r'^([A-Z]{1,5})(\d{6})([CP])(\d{8})$'
if not re.match(pattern, option_symbol.upper()):
    # Reconstruct if invalid
    ...
```

---

## 📊 EXAMPLES

### **Test Cases:**
- **AAPL** Dec 19, 2025, $267.50 Call → `AAPL251219C00267500`
- **TSLA** Dec 19, 2025, $481.90 Call → `TSLA251219C00481900`
- **META** Dec 19, 2025, $668.23 Call → `META251219C00668230`
- **MSFT** Dec 19, 2025, $485.00 Call → `MSFT251219C00485000`

### **Strike Formatting:**
- $267.50 → 267500 → `00267500` (8 digits)
- $481.90 → 481900 → `00481900` (8 digits)
- $668.23 → 668230 → `00668230` (8 digits)

---

## ✅ EXPECTED BEHAVIOR

### **Now:**
1. ✅ Option symbols formatted correctly before execution
2. ✅ Symbols validated against expected pattern
3. ✅ Symbols reconstructed from contract details if needed
4. ✅ Logs show formatted symbol: `Using option symbol: AAPL251219C00267500`

### **Benefits:**
- **Correct Format**: Symbols match Alpaca's expected format
- **Reliable Execution**: Orders will execute with correct symbol
- **Better Logging**: Clear visibility of option symbols being used

---

## 🎯 VALIDATION

Monitor logs for:
- `Using option symbol: [SYMBOL]` - Shows formatted symbol
- `Constructed option symbol: [SYMBOL]` - When symbol is built from details
- `Reformatted option symbol to: [SYMBOL]` - When symbol is corrected

---

**Fix applied and system restarted!**

