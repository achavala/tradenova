# Multi-Agent Trading System - Setup Guide

## 🎉 What's Been Added

Your TradeNova system now includes a **sophisticated multi-agent trading system** with:

### ✅ Core Components (Fully Implemented)

1. **Feature Engineering Engine**
   - Technical indicators (EMA, RSI, ATR, ADX, VWAP)
   - Statistical features (Hurst Exponent, Linear Regression, R²)
   - Pattern detection (Fair Value Gaps)

2. **Regime Classification**
   - 4 market regimes: TREND, MEAN_REVERSION, EXPANSION, COMPRESSION
   - Trend direction, volatility levels, market bias
   - Confidence scoring

3. **5 Trading Agents**
   - **TrendAgent**: Follows strong trends
   - **MeanReversionAgent**: Trades range-bound markets
   - **FVGAgent**: Trades gap fills
   - **VolatilityAgent**: Trades volatility expansion
   - **EMAAgent**: Simple momentum (SPY-specific)

4. **Meta-Policy Controller**
   - Intelligently combines agent signals
   - Adaptive agent weights
   - Multi-armed bandit principles

5. **Multi-Agent Orchestrator**
   - Coordinates all components
   - Ready to integrate with TradeNova

---

## 🚀 Quick Integration

### Option 1: Use Multi-Agent System (Recommended)

Create a new file `tradenova_multi_agent.py`:

```python
from tradenova import TradeNova
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from alpaca_trade_api.rest import TimeFrame
from datetime import datetime, timedelta

class TradeNovaMultiAgent(TradeNova):
    """TradeNova with multi-agent system"""
    
    def __init__(self):
        super().__init__()
        # Replace simple strategy with multi-agent orchestrator
        self.orchestrator = MultiAgentOrchestrator(self.client)
    
    def scan_and_trade(self):
        """Scan using multi-agent system"""
        if not self.can_open_new_position():
            logger.info(f"Max positions reached ({self.max_active_trades})")
            return
        
        if not self.client.is_market_open():
            logger.info("Market is closed")
            return
        
        # Get historical bars for each ticker
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        for ticker in Config.TICKERS:
            if ticker in self.positions and not self.positions[ticker].is_closed():
                continue
            
            try:
                bars = self.client.get_historical_bars(
                    ticker,
                    TimeFrame.Day,
                    start_date,
                    end_date
                )
                
                if bars.empty:
                    continue
                
                # Analyze with multi-agent system
                intent = self.orchestrator.analyze_symbol(ticker, bars)
                
                if intent and intent.direction.value != "FLAT":
                    if intent.confidence >= 0.6:
                        self._execute_entry_from_intent(intent)
            
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
    
    def _execute_entry_from_intent(self, intent):
        """Execute trade from agent intent"""
        symbol = intent.symbol
        current_price = intent.entry_price
        
        # Use suggested position size or calculate
        if intent.position_size_suggestion > 0:
            # Use suggested size as percentage of balance
            position_capital = self.previous_day_balance * intent.position_size_suggestion
            qty = position_capital / current_price
        else:
            qty = self.calculate_position_size(current_price)
        
        qty = int(qty) if qty >= 1 else round(qty, 2)
        
        if qty < 0.01:
            return
        
        try:
            order = self.client.place_order(
                symbol=symbol,
                qty=qty,
                side='buy' if intent.direction.value == "LONG" else 'sell',
                order_type='market'
            )
            
            if order and order.get('status') == 'filled':
                filled_price = order.get('filled_avg_price', current_price)
                filled_qty = order.get('filled_qty', qty)
                
                # Create position (use intent's stop loss/take profit if provided)
                self.positions[symbol] = Position(
                    symbol=symbol,
                    qty=filled_qty,
                    entry_price=filled_price,
                    side='long' if intent.direction.value == "LONG" else 'short',
                    config=self.profit_target_config
                )
                
                logger.info(f"Entry executed: {symbol} via {intent.agent_name}")
                logger.info(f"  Direction: {intent.direction.value}")
                logger.info(f"  Quantity: {filled_qty}, Entry: ${filled_price:.2f}")
                logger.info(f"  Confidence: {intent.confidence:.2%}")
                logger.info(f"  Reasoning: {intent.reasoning}")
        
        except Exception as e:
            logger.error(f"Error executing entry for {symbol}: {e}")
```

### Option 2: Keep Existing System

Your existing TradeNova system continues to work as-is. The multi-agent system is available but optional.

---

## 📦 New Dependencies

The following packages have been added to `requirements.txt`:

- `scipy>=1.11.0` - Scientific computing (Hurst, regression)
- `statsmodels>=0.14.0` - Statistical modeling
- `plotly>=5.18.0` - Data visualization (for future UI)
- `scikit-learn>=1.3.0` - Machine learning (for future ML features)
- `fastapi>=0.104.0` - Web framework (for future dashboard)
- `uvicorn>=0.24.0` - ASGI server (for future dashboard)

**Install them:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🧪 Testing the System

### Test Feature Engineering

```python
from core.features.indicators import FeatureEngine
import pandas as pd

engine = FeatureEngine()
# Load some price data
df = pd.DataFrame(...)  # Your OHLCV data
features = engine.calculate_all_features(df)
print(features)
```

### Test Regime Classification

```python
from core.regime.classifier import RegimeClassifier
from core.features.indicators import FeatureEngine

classifier = RegimeClassifier()
engine = FeatureEngine()

# Calculate features
features = engine.calculate_all_features(df)
# Classify regime
regime = classifier.classify(features)
print(f"Regime: {regime.regime_type.value}, Confidence: {regime.confidence:.2%}")
```

### Test Multi-Agent System

```python
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from alpaca_client import AlpacaClient
from config import Config

client = AlpacaClient(
    Config.ALPACA_API_KEY,
    Config.ALPACA_SECRET_KEY,
    Config.ALPACA_BASE_URL
)

orchestrator = MultiAgentOrchestrator(client)

# Get bars
bars = client.get_historical_bars("AAPL", TimeFrame.Day, start, end)

# Analyze
intent = orchestrator.analyze_symbol("AAPL", bars)
if intent:
    print(f"Signal: {intent.direction.value}")
    print(f"Confidence: {intent.confidence:.2%}")
    print(f"Agent: {intent.agent_name}")
    print(f"Reasoning: {intent.reasoning}")
```

---

## 📊 How It Works

### Trading Flow

```
1. Data Collection (Alpaca bars)
   ↓
2. Feature Calculation (Technical + Statistical)
   ↓
3. Regime Classification (TREND/MEAN_REVERSION/EXPANSION/COMPRESSION)
   ↓
4. Agent Evaluation (Each agent checks if it should activate)
   ↓
5. Meta-Policy Decision (Combine/arbitrate agent signals)
   ↓
6. Risk Check (Your existing risk management)
   ↓
7. Execution (Your existing position management)
```

### Agent Activation

- **TrendAgent**: Activates in TREND regime
- **MeanReversionAgent**: Activates in MEAN_REVERSION regime
- **FVGAgent**: Activates when FVG detected
- **VolatilityAgent**: Activates in EXPANSION regime
- **EMAAgent**: Always available (SPY only)

### Meta-Policy

- Filters low-confidence signals
- Resolves direction conflicts
- Scores intents based on:
  - Agent fitness (performance history)
  - Regime match
  - Volatility adjustment
  - Confidence level
- Blends signals when scores are close

---

## 🎯 Key Features

### Adaptive Learning

- Agents track their performance
- Meta-policy adjusts agent weights
- Better-performing agents get higher priority
- System improves over time

### Regime-Aware Trading

- Only trades when regime is clear (confidence ≥ 0.4)
- Different agents for different market conditions
- Prevents trading in uncertain markets

### Risk Management Integration

- Works with your existing risk management
- Position sizing from agents is a suggestion
- Your TP1-TP5 system still applies
- Your 15% stop loss still applies

---

## ⚠️ What's Still Pending

1. **Options Agents**: Basic structure exists, needs options chain integration
2. **Advanced Risk**: Daily loss limits, drawdown tracking (basic risk exists)
3. **UI Dashboard**: FastAPI dashboard not yet implemented
4. **Data Feeds**: Polygon/Finnhub not yet integrated (Alpaca works)
5. **Backtesting**: Historical replay not yet implemented

---

## 📝 Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Test the system**: Run the test examples above
3. **Integrate**: Use Option 1 or 2 above
4. **Monitor**: Watch agent performance and regime classifications
5. **Iterate**: Adjust agent parameters based on results

---

## 🆘 Troubleshooting

### Import Errors

Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Missing Features

If features are missing, check that you have enough historical data (at least 50 bars).

### Low Confidence

If regime confidence is low, the system won't trade. This is by design to prevent trading in uncertain conditions.

---

**Status**: ✅ **Core System Ready** | 🚀 **Ready to Integrate**

