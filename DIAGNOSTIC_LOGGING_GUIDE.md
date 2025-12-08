# 🔍 Diagnostic Logging Guide - Trade Barrier Analysis

## ✅ **DIAGNOSTIC LOGGING IMPLEMENTED**

### New Log Tags

1. **`[SIGNAL]`** - Signal Generation Tracking
   - Shows every signal generation attempt
   - Includes: symbol, action, confidence, agent, reason
   - Format: `[SIGNAL] SYMBOL | has_signal=BOOL | action=ACTION | confidence=X.XX | agent=AGENT`

2. **`[SKIP]`** - Trade Filter Tracking
   - Shows exactly why trades are being filtered
   - Includes: symbol, reason, confidence, risk_ok, has_position
   - Format: `[SKIP] SYMBOL | reason=REASON | conf=X.XX | risk_ok=BOOL | has_position=BOOL`

---

## 🔍 **HOW TO ANALYZE**

### Step 1: Check Signal Generation

```bash
grep "[SIGNAL]" logs/tradenova_daemon.log | tail -20
```

**What to look for:**
- `has_signal=True` → Signals are being generated
- `has_signal=False` → No signals (check reason)
- `confidence=X.XX` → Confidence levels

**Questions:**
- Are signals being generated at all?
- What are the confidence numbers?
- Are they all below 0.50 (50%)?

### Step 2: Check Trade Filters

```bash
grep "[SKIP]" logs/tradenova_daemon.log | tail -20
```

**Skip Reasons:**
- `NO_SIGNAL` → No signal generated
- `DATA_UNAVAILABLE` → Insufficient bars
- `LOW_CONFIDENCE: X.XX < 0.50` → Confidence too low
- `RISK_BLOCK: reason` → Risk manager blocking
- `HAS_POSITION` → Already have position (one-trade-per-symbol)

**Questions:**
- What's the most common skip reason?
- Are signals being generated but filtered?
- Is confidence the main barrier?

### Step 3: Combined Analysis

```bash
# See signal generation and filtering together
grep -E "\[SIGNAL\]|\[SKIP\]" logs/tradenova_daemon.log | tail -40
```

---

## 📊 **EXPECTED LOG PATTERNS**

### Pattern 1: Data Barrier (Should be fixed)
```
[SIGNAL] NVDA | has_signal=False | action=None | confidence=0.00 | reason=no_intents
[SKIP] NVDA | reason=DATA_UNAVAILABLE | bars=44 | need=30+
```
**Status**: Should NOT see this anymore (30-bar threshold)

### Pattern 2: Low Confidence
```
[SIGNAL] NVDA | has_signal=True | action=LONG | confidence=0.35 | agent=TrendAgent
[SKIP] NVDA | reason=LOW_CONFIDENCE: 0.35 < 0.50 | conf=0.35 | risk_ok=True | has_position=False
```
**Status**: Signals generated but confidence too low

### Pattern 3: Risk Block
```
[SIGNAL] NVDA | has_signal=True | action=LONG | confidence=0.65 | agent=TrendAgent
[SKIP] NVDA | reason=RISK_BLOCK: daily_loss_limit | conf=0.65 | risk_ok=False | has_position=False
```
**Status**: Signal good but risk manager blocking

### Pattern 4: Already Has Position
```
[SIGNAL] NVDA | has_signal=True | action=LONG | confidence=0.75 | agent=TrendAgent
[SKIP] NVDA | reason=HAS_POSITION: one-trade-per-symbol rule | conf=0.75 | risk_ok=True | has_position=True
```
**Status**: Signal good but already have position

### Pattern 5: Trade Executes
```
[SIGNAL] NVDA | has_signal=True | action=LONG | confidence=0.75 | agent=TrendAgent
✅ EXECUTING TRADE: NVDA LONG (confidence: 0.75, agent: TrendAgent, ...)
```
**Status**: ✅ Trade executes!

---

## 🎯 **DIAGNOSIS WORKFLOW**

1. **Check if data barrier is gone:**
   ```bash
   grep "Data available" logs/tradenova_daemon.log | tail -10
   ```
   Should see: `✅ SYMBOL: Data available (X bars)`

2. **Check signal generation:**
   ```bash
   grep "\[SIGNAL\]" logs/tradenova_daemon.log | grep "has_signal=True" | tail -10
   ```
   Count how many signals are generated

3. **Check confidence distribution:**
   ```bash
   grep "\[SIGNAL\]" logs/tradenova_daemon.log | grep "confidence=" | tail -20
   ```
   Are they all below 0.50?

4. **Check skip reasons:**
   ```bash
   grep "\[SKIP\]" logs/tradenova_daemon.log | cut -d'|' -f2 | sort | uniq -c
   ```
   Shows count of each skip reason

---

## 🔧 **DEBUGGING ACTIONS**

### If No Signals Generated:
- Check orchestrator logs for agent errors
- Check feature engine for calculation issues
- Check regime classifier confidence

### If Signals But Low Confidence:
- Temporarily lower threshold to 0.35 for testing
- Check if trades execute
- If yes → threshold is too strict for current market

### If Signals But Risk Block:
- Check risk manager status
- Review daily loss limits
- Check position limits

### If Signals But Has Position:
- This is expected (one-trade-per-symbol rule)
- Check if positions should be closed first

---

## 📝 **NEXT STEPS**

1. **Restart daemon** to pick up code changes:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.tradenova.plist
   launchctl load ~/Library/LaunchAgents/com.tradenova.plist
   ```

2. **Wait for next trading cycle** (5 minutes)

3. **Analyze logs** using the commands above

4. **Report findings**:
   - How many signals generated?
   - What confidence levels?
   - What skip reasons?
   - Any trades executed?

---

## ✅ **SUMMARY**

Diagnostic logging is now in place to pinpoint exactly where trades are being filtered. Use the `[SIGNAL]` and `[SKIP]` tags to trace the full pipeline from data → signals → filters → execution.

