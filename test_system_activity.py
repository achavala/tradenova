#!/usr/bin/env python3
"""
Test System Activity - Verify signals and trading capability
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_system():
    """Test if system can generate signals"""
    logger.info("="*70)
    logger.info("TESTING SYSTEM ACTIVITY")
    logger.info("="*70)
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    orchestrator = MultiAgentOrchestrator(client)
    
    # Check account
    account = client.get_account()
    logger.info(f"\n✅ Account Status:")
    logger.info(f"   Equity: ${account['equity']:,.2f}")
    logger.info(f"   Cash: ${account['cash']:,.2f}")
    logger.info(f"   Market Open: {client.is_market_open()}")
    
    # Test signal generation for a few tickers
    logger.info(f"\n📊 Testing Signal Generation...")
    logger.info(f"{'='*70}")
    
    signals_found = 0
    test_tickers = Config.TICKERS[:5]  # Test first 5
    
    for ticker in test_tickers:
        try:
            # Get recent bars
            end = datetime.now()
            start = end - timedelta(days=30)
            
            bars = client.get_historical_bars(
                ticker,
                TimeFrame.Day,
                start,
                end
            )
            
            if bars.empty or len(bars) < 20:
                logger.warning(f"  {ticker}: Insufficient data")
                continue
            
            # Analyze
            trade_intent = orchestrator.analyze_symbol(ticker, bars)
            
            if trade_intent:
                signals_found += 1
                logger.info(f"  ✅ {ticker}: {trade_intent.direction.value} ({trade_intent.confidence:.2%}) - {trade_intent.agent_name}")
            else:
                logger.info(f"  ⏸️  {ticker}: No signal (confidence too low)")
                
        except Exception as e:
            logger.error(f"  ❌ {ticker}: Error - {e}")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📈 RESULTS:")
    logger.info(f"   Tickers Tested: {len(test_tickers)}")
    logger.info(f"   Signals Generated: {signals_found}")
    logger.info(f"   Signal Rate: {signals_found/len(test_tickers)*100:.1f}%")
    
    if signals_found > 0:
        logger.info(f"\n✅ System is generating signals!")
        logger.info(f"   The system would execute trades when:")
        logger.info(f"   - Market is open")
        logger.info(f"   - Confidence >= 30%")
        logger.info(f"   - Under position limits")
    else:
        logger.warning(f"\n⚠️  No signals generated")
        logger.info(f"   This could mean:")
        logger.info(f"   - Market conditions don't meet criteria")
        logger.info(f"   - Confidence thresholds are high")
        logger.info(f"   - Need to check signal generation logic")
    
    logger.info("="*70)

if __name__ == "__main__":
    test_system()

