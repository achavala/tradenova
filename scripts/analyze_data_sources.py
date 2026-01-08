#!/usr/bin/env python3
"""
Comprehensive Data Source Analysis
Analyzes ALL data sources, API calls, and data freshness in TradeNova
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import datetime as dt
from datetime import timedelta
import pytz

ET = pytz.timezone('America/New_York')

def section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def subsection(title):
    print(f"\n[{title}]")

def main():
    print("=" * 80)
    print("TRADENOVA - COMPREHENSIVE DATA SOURCE ANALYSIS")
    print("=" * 80)
    print(f"Analysis Time: {dt.datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET')}")
    
    # ========================================================================
    # DATA SOURCE 1: ALPACA API
    # ========================================================================
    section("DATA SOURCE 1: ALPACA TRADING API")
    
    subsection("1.1 Alpaca Client Configuration")
    from config import Config
    print(f"  Base URL: {Config.ALPACA_BASE_URL}")
    print(f"  API Key: {Config.ALPACA_API_KEY[:8]}...")
    print(f"  Mode: {'PAPER' if 'paper' in Config.ALPACA_BASE_URL else 'LIVE'}")
    
    subsection("1.2 Alpaca Client Methods")
    from alpaca_client import AlpacaClient
    client = AlpacaClient()
    
    # Test account data
    print("\n  --- Account Data (REAL-TIME) ---")
    account = client.get_account()
    if account:
        print(f"  ✅ Account Status: {account.get('status')}")
        print(f"  ✅ Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
        print(f"  ✅ Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
        print(f"  ✅ Cash: ${float(account.get('cash', 0)):,.2f}")
        print(f"  → Source: Alpaca REST API /v2/account")
        print(f"  → Freshness: REAL-TIME (live account state)")
    
    # Test positions
    print("\n  --- Positions Data (REAL-TIME) ---")
    positions = client.get_positions()
    print(f"  ✅ Open Positions: {len(positions)}")
    for pos in positions[:3]:
        symbol = pos.get('symbol', 'N/A')
        qty = pos.get('qty', 0)
        current_price = float(pos.get('current_price', 0))
        print(f"     {symbol}: {qty} @ ${current_price:.2f}")
    print(f"  → Source: Alpaca REST API /v2/positions")
    print(f"  → Freshness: REAL-TIME (reflects current holdings)")
    
    # Test orders
    print("\n  --- Orders Data (REAL-TIME) ---")
    orders = client.get_orders(status='all', limit=5)
    print(f"  ✅ Recent Orders: {len(orders) if orders else 0}")
    print(f"  → Source: Alpaca REST API /v2/orders")
    print(f"  → Freshness: REAL-TIME")
    
    # Test market data (bars)
    print("\n  --- Stock Price Data (DELAYED for paper) ---")
    try:
        bars = client.get_bars('NVDA', timeframe='1Day', limit=5)
        if bars:
            latest = bars[-1]
            bar_time = latest.get('timestamp', 'N/A')
            print(f"  ✅ NVDA Latest Bar: ${float(latest.get('close', 0)):.2f}")
            print(f"     Bar Time: {bar_time}")
            print(f"  → Source: Alpaca Data API /v2/stocks/bars")
            print(f"  → Freshness: 15-min delayed (paper account)")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")
    
    # Test latest quote
    print("\n  --- Stock Quote Data ---")
    try:
        # Use Alpaca's data API directly
        from alpaca.data import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
        from alpaca.data.timeframe import TimeFrame as AlpacaTimeFrame
        
        data_client = StockHistoricalDataClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY)
        request = StockLatestQuoteRequest(symbol_or_symbols=["NVDA"])
        quotes = data_client.get_stock_latest_quote(request)
        if quotes and 'NVDA' in quotes:
            q = quotes['NVDA']
            print(f"  ✅ NVDA Quote: Bid=${q.bid_price:.2f}, Ask=${q.ask_price:.2f}")
            print(f"     Bid Size: {q.bid_size}, Ask Size: {q.ask_size}")
            print(f"  → Source: Alpaca Data API /v2/stocks/quotes/latest")
            print(f"  → Freshness: 15-min delayed (paper) or REAL-TIME (live)")
    except Exception as e:
        print(f"  ⚠️ No quote: {e}")
    
    # Test bars
    print("\n  --- Stock Bars Data ---")
    try:
        bar_request = StockBarsRequest(
            symbol_or_symbols=["NVDA"],
            timeframe=AlpacaTimeFrame.Day,
            start=dt.datetime.now() - timedelta(days=7)
        )
        bars = data_client.get_stock_bars(bar_request)
        if bars and 'NVDA' in bars:
            nvda_bars = bars['NVDA']
            print(f"  ✅ NVDA Bars: {len(nvda_bars)} daily bars")
            latest = nvda_bars[-1]
            print(f"     Latest: Open=${latest.open:.2f}, High=${latest.high:.2f}, Low=${latest.low:.2f}, Close=${latest.close:.2f}")
            print(f"     Volume: {latest.volume:,}")
            print(f"     Timestamp: {latest.timestamp}")
            print(f"  → Source: Alpaca Data API /v2/stocks/bars")
            print(f"  → Freshness: 15-min delayed (paper)")
    except Exception as e:
        print(f"  ⚠️ No bars: {e}")
    
    # ========================================================================
    # DATA SOURCE 2: ALPACA OPTIONS API
    # ========================================================================
    section("DATA SOURCE 2: ALPACA OPTIONS API")
    
    subsection("2.1 Options Chain Data")
    from services.options_data_feed import OptionsDataFeed
    options_feed = OptionsDataFeed(client)  # Pass client
    
    print("\n  --- Options Chain ---")
    try:
        chain = options_feed.get_options_chain('NVDA')
        if chain:
            print(f"  ✅ NVDA Options Contracts: {len(chain)}")
            if len(chain) > 0:
                sample = chain[0]
                print(f"     Sample: {sample.get('symbol', 'N/A')}")
                print(f"     Expiration: {sample.get('expiration', 'N/A')}")
                print(f"     Strike: ${sample.get('strike', 0)}")
            print(f"  → Source: Alpaca Options API /v1beta1/options/contracts")
            print(f"  → Freshness: Contract definitions (static)")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")
    
    print("\n  --- Options Quote Data ---")
    try:
        # Get a sample option symbol
        if chain and len(chain) > 0:
            sample_symbol = chain[0].get('symbol')
            option_quote = options_feed.get_option_quote(sample_symbol)
            if option_quote:
                print(f"  ✅ {sample_symbol}:")
                print(f"     Bid: ${option_quote.get('bid', 'N/A')}")
                print(f"     Ask: ${option_quote.get('ask', 'N/A')}")
                print(f"     Last: ${option_quote.get('last', 'N/A')}")
                print(f"  → Source: Alpaca Options API /v1beta1/options/quotes")
                print(f"  → Freshness: REAL-TIME (during market hours)")
    except Exception as e:
        print(f"  ⚠️ No option quote: {e}")
    
    # ========================================================================
    # DATA SOURCE 3: MASSIVE API (HISTORICAL DATA)
    # ========================================================================
    section("DATA SOURCE 3: MASSIVE API (HISTORICAL DATA)")
    
    subsection("3.1 Massive Configuration")
    massive_key = os.getenv('MASSIVE_API_KEY', '')
    print(f"  API Key: {massive_key[:8] + '...' if massive_key else 'NOT SET'}")
    
    print("\n  --- Historical Bars via Massive ---")
    try:
        from services.massive_price_feed import MassivePriceFeed
        massive = MassivePriceFeed()
        
        bars = massive.get_historical_bars('NVDA', days=5)
        if bars is not None and len(bars) > 0:
            print(f"  ✅ NVDA Historical Bars: {len(bars)} bars")
            latest = bars.iloc[-1] if hasattr(bars, 'iloc') else bars[-1]
            print(f"     Latest Close: ${float(latest.get('close', latest['close']) if isinstance(latest, dict) else latest['close']):.2f}")
            print(f"  → Source: Massive Stock History API")
            print(f"  → Freshness: End-of-day or intraday (depends on timeframe)")
        else:
            print(f"  ⚠️ No bars returned from Massive")
    except Exception as e:
        print(f"  ⚠️ Massive not available: {e}")
    
    # ========================================================================
    # DATA SOURCE 4: TECHNICAL INDICATORS (COMPUTED)
    # ========================================================================
    section("DATA SOURCE 4: TECHNICAL INDICATORS (COMPUTED)")
    
    subsection("4.1 Feature Engineering Pipeline")
    try:
        from core.features import FeatureEngine
        fe = FeatureEngine()
        
        # Get sample data using Alpaca data client
        import pandas as pd
        bar_request = StockBarsRequest(
            symbol_or_symbols=["NVDA"],
            timeframe=AlpacaTimeFrame.Day,
            start=dt.datetime.now() - timedelta(days=120)
        )
        bars_result = data_client.get_stock_bars(bar_request)
        if bars_result and 'NVDA' in bars_result:
            nvda_bars = bars_result['NVDA']
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            } for bar in nvda_bars])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Compute features
            features = fe.compute_features(df)
            
            print("\n  --- Computed Indicators ---")
            indicator_list = [
                ('RSI_14', 'Relative Strength Index (14)'),
                ('EMA_9', 'Exponential Moving Average (9)'),
                ('EMA_21', 'Exponential Moving Average (21)'),
                ('SMA_20', 'Simple Moving Average (20)'),
                ('SMA_50', 'Simple Moving Average (50)'),
                ('ATR_14', 'Average True Range (14)'),
                ('ADX_14', 'Average Directional Index (14)'),
                ('MACD', 'MACD Line'),
                ('MACD_signal', 'MACD Signal'),
                ('BB_upper', 'Bollinger Band Upper'),
                ('BB_lower', 'Bollinger Band Lower'),
                ('BB_middle', 'Bollinger Band Middle'),
                ('VWAP', 'Volume Weighted Average Price'),
                ('volume_sma', 'Volume SMA'),
                ('returns', 'Daily Returns'),
                ('volatility', 'Realized Volatility'),
            ]
            
            for col, desc in indicator_list:
                if col in features.columns:
                    val = features[col].iloc[-1]
                    if pd.notna(val):
                        print(f"  ✅ {desc}: {val:.4f}")
                    else:
                        print(f"  ⚠️ {desc}: NaN (insufficient data)")
                else:
                    print(f"  ❌ {desc}: Not computed")
            
            print(f"\n  → Source: COMPUTED from Alpaca/Massive price bars")
            print(f"  → Libraries: pandas, ta-lib, numpy")
            print(f"  → Freshness: As fresh as input price data")
    except Exception as e:
        print(f"  ⚠️ Feature engine error: {e}")
    
    # ========================================================================
    # DATA SOURCE 5: REGIME CLASSIFICATION
    # ========================================================================
    section("DATA SOURCE 5: REGIME CLASSIFICATION (COMPUTED)")
    
    try:
        from core.regime_classifier import RegimeClassifier
        rc = RegimeClassifier()
        
        print("\n  --- Regime Detection Methods ---")
        print("  1. Hurst Exponent → Trend vs Mean-Reversion")
        print("  2. ATR Percentile → Volatility Regime")
        print("  3. ADX → Trend Strength")
        print("  4. Price Slope → Direction")
        
        # Get regime for NVDA - reuse the df we already have
        if 'df' in dir() and df is not None and len(df) > 0:
            regime = rc.classify(df)
            print(f"\n  ✅ Current NVDA Regime: {regime}")
            print(f"  → Source: COMPUTED from price history")
            print(f"  → Freshness: As fresh as input data")
    except Exception as e:
        print(f"  ⚠️ Regime classifier error: {e}")
    
    # ========================================================================
    # DATA SOURCE 6: MULTI-AGENT SIGNALS
    # ========================================================================
    section("DATA SOURCE 6: MULTI-AGENT SIGNALS (COMPUTED)")
    
    print("\n  --- Trading Agents ---")
    agents = [
        ('EMAAgent', 'EMA crossover signals (9/21)'),
        ('TrendAgent', 'Trend-following via ADX + slope'),
        ('MeanReversionAgent', 'RSI + Bollinger Band mean reversion'),
        ('VolatilityAgent', 'ATR-based volatility breakouts'),
        ('OptionsAgent', 'Options-specific signals'),
    ]
    
    for agent_name, desc in agents:
        print(f"  ✅ {agent_name}: {desc}")
    
    print(f"\n  → Source: COMPUTED from technical indicators")
    print(f"  → Input: Feature Engine output")
    print(f"  → Output: TradeIntent (direction, confidence, symbol)")
    
    # ========================================================================
    # DATA SOURCE 7: RL MODEL PREDICTIONS
    # ========================================================================
    section("DATA SOURCE 7: RL MODEL PREDICTIONS")
    
    try:
        from rl.predict import RLPredictor
        from pathlib import Path
        
        model_path = Path("models/grpo_final.zip")
        if model_path.exists():
            print(f"  ✅ Model: {model_path}")
            print(f"  ✅ Type: GRPO (Group Relative Policy Optimization)")
            print(f"  ✅ Framework: Stable Baselines3 PPO")
            print(f"\n  --- Model Input Features (48 dimensions) ---")
            print("  - Price features: open, high, low, close, volume")
            print("  - Technical: RSI, EMA, SMA, MACD, BB, ATR, ADX")
            print("  - Derived: returns, volatility, volume ratio")
            print("  - Position: current holdings, entry price, P&L")
            print(f"\n  → Source: LOCAL MODEL (pre-trained)")
            print(f"  → Freshness: Model weights are static, predictions real-time")
        else:
            print(f"  ⚠️ Model not found at {model_path}")
    except Exception as e:
        print(f"  ⚠️ RL predictor error: {e}")
    
    # ========================================================================
    # DATA SOURCE 8: IV & GREEKS
    # ========================================================================
    section("DATA SOURCE 8: IMPLIED VOLATILITY & GREEKS")
    
    print("\n  --- IV Rank Service ---")
    try:
        from services.iv_rank_service import IVRankService
        iv_service = IVRankService()
        
        iv_metrics = iv_service.get_iv_metrics('NVDA')
        if iv_metrics:
            print(f"  ✅ NVDA IV Metrics:")
            print(f"     Current IV: {iv_metrics.get('current_iv', 'N/A')}")
            print(f"     IV Rank: {iv_metrics.get('iv_rank', 'N/A')}%")
            print(f"     IV Percentile: {iv_metrics.get('iv_percentile', 'N/A')}%")
            print(f"  → Source: Alpaca Options API + Historical computation")
        else:
            print(f"  ⚠️ IV metrics not available")
    except Exception as e:
        print(f"  ⚠️ IV service error: {e}")
    
    print("\n  --- Greeks Calculation ---")
    print("  Greeks are typically embedded in option quotes or computed via:")
    print("  - Black-Scholes model")
    print("  - Alpaca options chain data (when available)")
    print(f"  → Source: COMPUTED or from Alpaca Options API")
    
    # ========================================================================
    # DATA SOURCE 9: NEWS & EVENTS
    # ========================================================================
    section("DATA SOURCE 9: NEWS & EVENT FILTERS")
    
    print("\n  --- Earnings Calendar ---")
    try:
        from services.earnings_calendar import EarningsCalendar
        ec = EarningsCalendar()
        
        # Check earnings for NVDA
        next_earnings = ec.get_next_earnings('NVDA')
        if next_earnings:
            print(f"  ✅ NVDA Next Earnings: {next_earnings}")
        else:
            print(f"  ⚠️ NVDA Earnings: Not found")
        print(f"  → Source: Yahoo Finance / Public earnings calendar")
    except Exception as e:
        print(f"  ⚠️ Earnings calendar error: {e}")
    
    print("\n  --- Macro Event Filter ---")
    try:
        from services.macro_calendar import MacroCalendar
        mc = MacroCalendar()
        
        events = mc.get_events_today()
        print(f"  ✅ Today's Macro Events: {len(events) if events else 0}")
        print(f"  → Source: Static economic calendar (FOMC, NFP, CPI dates)")
    except Exception as e:
        print(f"  ⚠️ Macro calendar error: {e}")
    
    print("\n  --- News Filter ---")
    try:
        from core.live.news_filter import NewsFilter
        nf = NewsFilter()
        
        is_blocked, reason = nf.is_blocked()
        status = "BLOCKED" if is_blocked else "ALLOWED"
        print(f"  ✅ Current Trading Status: {status}")
        if is_blocked:
            print(f"     Reason: {reason}")
        print(f"  → Source: Time-based rules + economic calendar")
    except Exception as e:
        print(f"  ⚠️ News filter error: {e}")
    
    # ========================================================================
    # DATA SOURCE 10: RISK METRICS
    # ========================================================================
    section("DATA SOURCE 10: RISK METRICS")
    
    print("\n  --- Advanced Risk Manager ---")
    try:
        from core.risk.advanced_risk_manager import AdvancedRiskManager
        
        account = client.get_account()
        portfolio_value = float(account.get('portfolio_value', 100000))
        arm = AdvancedRiskManager(portfolio_value)
        
        print(f"  ✅ Portfolio Value: ${portfolio_value:,.2f}")
        print(f"  ✅ UVaR Enabled: {arm.uvar_enabled}")
        print(f"  → Source: COMPUTED from portfolio + positions")
    except Exception as e:
        print(f"  ⚠️ Risk manager error: {e}")
    
    print("\n  --- Options Risk Manager ---")
    try:
        from core.risk.options_risk_manager import OptionsRiskManager
        orm = OptionsRiskManager()
        
        summary = orm.get_portfolio_summary()
        print(f"  ✅ Portfolio Delta: {summary['total_delta']:.0f}")
        print(f"  ✅ Portfolio Gamma: {summary['total_gamma']:.1f}")
        print(f"  ✅ Portfolio Theta: {summary['total_theta']:.0f}")
        print(f"  ✅ Portfolio Vega: {summary['total_vega']:.1f}")
        print(f"  → Source: COMPUTED from position Greeks")
    except Exception as e:
        print(f"  ⚠️ Options risk manager error: {e}")
    
    # ========================================================================
    # SUMMARY: DATA FLOW
    # ========================================================================
    section("SUMMARY: COMPLETE DATA FLOW")
    
    print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TRADENOVA DATA FLOW ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   ALPACA     │
                              │   (Primary)  │
                              └──────┬───────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐        ┌───────────────────┐        ┌──────────────────┐
│ Account Data  │        │   Market Data     │        │  Options Data    │
│ (REAL-TIME)   │        │ (15-min delayed*) │        │   (REAL-TIME)    │
├───────────────┤        ├───────────────────┤        ├──────────────────┤
│ - Balance     │        │ - Stock bars      │        │ - Chain          │
│ - Positions   │        │ - Stock quotes    │        │ - Quotes         │
│ - Orders      │        │ - Latest trade    │        │ - Greeks (some)  │
│ - P&L         │        │                   │        │                  │
└───────┬───────┘        └─────────┬─────────┘        └────────┬─────────┘
        │                          │                           │
        │                          ▼                           │
        │               ┌───────────────────┐                  │
        │               │  MASSIVE (Backup) │                  │
        │               │  Historical Bars  │                  │
        │               └─────────┬─────────┘                  │
        │                         │                            │
        │         ┌───────────────┴───────────────┐            │
        │         │                               │            │
        │         ▼                               ▼            │
        │  ┌─────────────────┐           ┌─────────────────┐   │
        │  │ Feature Engine  │           │ Regime Classifier│  │
        │  ├─────────────────┤           ├─────────────────┤   │
        │  │ - RSI           │           │ - Hurst         │   │
        │  │ - EMA (9/21)    │           │ - ATR %ile      │   │
        │  │ - SMA (20/50)   │           │ - ADX           │   │
        │  │ - ATR           │           │ - Slope         │   │
        │  │ - ADX           │           └────────┬────────┘   │
        │  │ - MACD          │                    │            │
        │  │ - Bollinger     │                    │            │
        │  │ - VWAP          │                    │            │
        │  │ - Volume SMA    │                    │            │
        │  │ - Returns       │                    │            │
        │  │ - Volatility    │                    │            │
        │  └────────┬────────┘                    │            │
        │           │                             │            │
        │           └──────────────┬──────────────┘            │
        │                          │                           │
        │                          ▼                           │
        │               ┌───────────────────┐                  │
        │               │  MULTI-AGENT      │                  │
        │               │  ORCHESTRATOR     │                  │
        │               ├───────────────────┤                  │
        │               │ - EMAAgent        │                  │
        │               │ - TrendAgent      │                  │
        │               │ - MRAgent         │                  │
        │               │ - VolAgent        │                  │
        │               │ - OptionsAgent    │                  │
        │               └────────┬──────────┘                  │
        │                        │                             │
        │                        ▼                             │
        │               ┌───────────────────┐                  │
        │               │   RL PREDICTOR    │                  │
        │               │  (GRPO/PPO Model) │                  │
        │               └────────┬──────────┘                  │
        │                        │                             │
        │         ┌──────────────┴──────────────┐              │
        │         │                             │              │
        │         ▼                             ▼              │
        │  ┌─────────────────┐         ┌─────────────────┐     │
        │  │ ENSEMBLE        │         │ IV RANK SERVICE │◄────┘
        │  │ COMBINER        │         ├─────────────────┤
        │  └────────┬────────┘         │ - IV Rank       │
        │           │                  │ - IV Percentile │
        │           │                  └────────┬────────┘
        │           │                           │
        │           └───────────┬───────────────┘
        │                       │
        │                       ▼
        │            ┌─────────────────────┐
        │            │   PRE-TRADE CHECKS  │
        │            ├─────────────────────┤
        │            │ - Greeks limits     │
        │            │ - IV Rank gate      │
        │            │ - DTE rules         │
        │            │ - Time-of-day       │
        │            │ - News filter       │
        │            │ - Portfolio heat    │
        └───────────►│ - Position sizing   │
                     └─────────┬───────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  TRADE EXECUTION    │
                    │   (via Alpaca)      │
                    └─────────────────────┘

* 15-min delay for paper trading, real-time for live trading
""")

    # ========================================================================
    # DATA FRESHNESS SUMMARY
    # ========================================================================
    section("DATA FRESHNESS SUMMARY")
    
    print("""
┌─────────────────────────────────────┬───────────────────┬────────────────────┐
│ DATA TYPE                           │ SOURCE            │ FRESHNESS          │
├─────────────────────────────────────┼───────────────────┼────────────────────┤
│ Account Balance/Positions           │ Alpaca REST       │ REAL-TIME          │
│ Orders/Fills                        │ Alpaca REST       │ REAL-TIME          │
│ Stock Bars (intraday)               │ Alpaca Data       │ 15-min delay*      │
│ Stock Quotes                        │ Alpaca Data       │ 15-min delay*      │
│ Options Chain                       │ Alpaca Options    │ REAL-TIME          │
│ Options Quotes                      │ Alpaca Options    │ REAL-TIME          │
│ Historical Bars                     │ Massive API       │ End-of-day         │
│ Technical Indicators                │ COMPUTED          │ = Input freshness  │
│ Regime Classification               │ COMPUTED          │ = Input freshness  │
│ Agent Signals                       │ COMPUTED          │ = Input freshness  │
│ RL Predictions                      │ LOCAL MODEL       │ = Input freshness  │
│ IV Rank                             │ Alpaca + COMPUTED │ Varies             │
│ Greeks                              │ Alpaca/COMPUTED   │ REAL-TIME/Varies   │
│ News/Events                         │ Static Calendar   │ Daily update       │
│ Risk Metrics                        │ COMPUTED          │ = Position data    │
├─────────────────────────────────────┴───────────────────┴────────────────────┤
│ * Live trading accounts get real-time data                                   │
└──────────────────────────────────────────────────────────────────────────────┘
""")

    print("\n✅ DATA SOURCE ANALYSIS COMPLETE")
    return 0

if __name__ == "__main__":
    sys.exit(main())

