# Test Suite - Validation Steps

## Overview

This test suite validates your options trading infrastructure in 3 steps:

1. **Data Layer Test** - Validates IV, GEX, and options chain data
2. **Single-Agent Test** - Validates individual agent logic
3. **Multi-Agent Orchestrator Test** - Validates end-to-end system

## Running the Tests

### Step 1: Data Pull Test

```bash
source venv/bin/activate
python tests/run_data_checks.py
```

**Expected Output:**
- Options chain data structure
- IV metrics (Rank, Percentile, statistics)
- GEX calculation results

### Step 2: Single-Agent Simulation

```bash
python tests/simulate_theta_harvester.py
```

**Expected Output:**
- Agent activation status
- Signal generation
- Agent decision process

### Step 3: Multi-Agent Orchestrator

```bash
python tests/run_orchestrator.py
```

**Expected Output:**
- Analysis results for multiple symbols
- Agent signals and decisions
- Agent performance status

## Run All Tests

```bash
python tests/run_data_checks.py && \
python tests/simulate_theta_harvester.py && \
python tests/run_orchestrator.py
```

## Notes

- Some tests may show warnings if Alpaca options API access is limited
- This is normal - the structure and logic are validated
- Tests will work fully once options API access is confirmed
- Sample data is generated when real data is unavailable

## Success Criteria

✅ All imports work
✅ Data layer structure correct
✅ Agent logic validated
✅ Orchestrator routing works
✅ End-to-end flow functional

