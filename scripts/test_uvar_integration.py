#!/usr/bin/env python3
"""
Test UVaR Integration
Validates UVaR calculation and integration with risk manager
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from core.risk.uvar_calculator import UVaRCalculator
from core.risk.advanced_risk_manager import AdvancedRiskManager
from alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_uvar_integration():
    """Test UVaR integration"""
    
    print("="*80)
    print("UVAR INTEGRATION TEST")
    print("="*80)
    print()
    
    # Initialize Alpaca client
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        print("✅ Alpaca client initialized")
    except Exception as e:
        print(f"❌ Could not initialize Alpaca client: {e}")
        return False
    
    # Initialize UVaR calculator
    uvar_calc = UVaRCalculator(
        alpaca_client=client,
        lookback_days=90,
        confidence_level=0.99
    )
    print("✅ UVaR calculator initialized")
    print()
    
    # Get current positions
    print("TEST 1: Get Current Positions")
    print("-" * 80)
    
    positions = client.get_positions()
    print(f"Current positions: {len(positions)}")
    
    if positions:
        for pos in positions:
            print(f"  {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f}")
    else:
        print("  No positions found")
        # Create sample positions for testing
        print("\n  Creating sample positions for testing...")
        positions = [
            {
                'symbol': 'NVDA',
                'qty': 10,
                'entry_price': 150.0,
                'current_price': 150.0
            },
            {
                'symbol': 'AAPL',
                'qty': 20,
                'entry_price': 180.0,
                'current_price': 180.0
            }
        ]
        print(f"  Sample positions: {len(positions)}")
    
    print()
    
    # Test UVaR calculation
    print("TEST 2: Calculate UVaR")
    print("-" * 80)
    
    if positions:
        # Convert Alpaca positions to UVaR format
        uvar_positions = []
        for pos in positions:
            uvar_positions.append({
                'symbol': pos['symbol'],
                'qty': float(pos['qty']) if pos.get('side', 'long') == 'long' else -float(pos['qty']),
                'entry_price': pos.get('avg_entry_price', pos.get('entry_price', 0)),
                'current_price': pos.get('current_price', pos.get('avg_entry_price', 0))
            })
        
        uvar_result = uvar_calc.calculate_uvar(uvar_positions, horizon_days=1)
        
        print(f"Portfolio Value: ${uvar_result['portfolio_value']:,.2f}")
        print(f"UVaR (1-day, 99%): ${uvar_result['uvar']:,.2f}")
        print(f"UVaR %: {uvar_result['uvar_pct']:.2f}%")
        print(f"Worst Case Loss: ${uvar_result['worst_case_loss']:,.2f}")
        print(f"Scenarios: {uvar_result['scenarios']}")
    else:
        print("⚠️  No positions to calculate UVaR")
    
    print()
    
    # Test UVaR breach check
    print("TEST 3: UVaR Breach Check")
    print("-" * 80)
    
    if positions:
        is_breach, reason, uvar_result = uvar_calc.check_uvar_breach(
            uvar_positions,
            max_uvar_pct=5.0,
            horizon_days=1
        )
        
        if is_breach:
            print(f"❌ UVaR BREACH: {reason}")
        else:
            print(f"✅ UVaR within limits: {reason}")
            print(f"   Current UVaR: {uvar_result['uvar_pct']:.2f}%")
            print(f"   Threshold: 5.0%")
    else:
        print("⚠️  No positions to check")
    
    print()
    
    # Test incremental UVaR
    print("TEST 4: Incremental UVaR")
    print("-" * 80)
    
    if positions:
        new_position = {
            'symbol': 'TSLA',
            'qty': 50,
            'entry_price': 250.0,
            'current_price': 250.0
        }
        
        incremental = uvar_calc.calculate_incremental_uvar(
            uvar_positions,
            new_position,
            horizon_days=1
        )
        
        print(f"UVaR Before: {incremental['uvar_before_pct']:.2f}%")
        print(f"UVaR After: {incremental['uvar_after_pct']:.2f}%")
        print(f"Incremental UVaR: {incremental['incremental_uvar_pct']:.2f}%")
        
        if incremental['uvar_after_pct'] > 5.0:
            print(f"⚠️  Adding position would breach 5% threshold")
        else:
            print(f"✅ Adding position is safe")
    else:
        print("⚠️  No positions to test incremental UVaR")
    
    print()
    
    # Test risk manager integration
    print("TEST 5: Risk Manager Integration")
    print("-" * 80)
    
    risk_manager = AdvancedRiskManager(
        initial_balance=100000,
        use_iv_regimes=True
    )
    
    # Enable UVaR
    risk_manager.enable_uvar(client, max_uvar_pct=5.0)
    
    if risk_manager.use_uvar:
        print("✅ UVaR enabled in risk manager")
        
        # Test trade allowance with UVaR
        if positions:
            # Convert to risk manager format
            current_positions = []
            for pos in positions:
                current_positions.append({
                    'symbol': pos['symbol'],
                    'qty': float(pos['qty']),
                    'entry_price': pos.get('avg_entry_price', 0),
                    'current_price': pos.get('current_price', 0)
                })
            
            # Test new trade
            allowed, reason, risk_level = risk_manager.check_trade_allowed(
                symbol='TSLA',
                qty=100,
                price=250.0,
                side='buy',
                current_positions=current_positions
            )
            
            print(f"Trade Allowed: {'✅ YES' if allowed else '❌ NO'}")
            print(f"Reason: {reason}")
            print(f"Risk Level: {risk_level.value}")
        else:
            print("⚠️  No positions to test trade allowance")
    else:
        print("❌ UVaR not enabled in risk manager")
    
    print()
    
    # Test risk status with UVaR
    print("TEST 6: Risk Status with UVaR")
    print("-" * 80)
    
    if positions and risk_manager.use_uvar:
        current_positions = []
        for pos in positions:
            current_positions.append({
                'symbol': pos['symbol'],
                'qty': float(pos['qty']),
                'entry_price': pos.get('avg_entry_price', 0),
                'current_price': pos.get('current_price', 0)
            })
        
        risk_status = risk_manager.get_risk_status(current_positions=current_positions)
        
        print(f"Risk Level: {risk_status['risk_level']}")
        if 'uvar' in risk_status:
            print(f"UVaR: ${risk_status['uvar']:,.2f}")
            print(f"UVaR %: {risk_status['uvar_pct']:.2f}%")
            print(f"UVaR Breach: {'❌ YES' if risk_status['uvar_breach'] else '✅ NO'}")
    else:
        print("⚠️  No positions or UVaR not enabled")
    
    print()
    
    print("="*80)
    print("✅ UVAR INTEGRATION TEST COMPLETE")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = test_uvar_integration()
    sys.exit(0 if success else 1)




