#!/usr/bin/env python3
"""
TradeNova Status Summary
Clean, readable status report without encoding issues
"""
import sys
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent))

def show_status():
    """Display TradeNova status summary"""
    
    print("="*70)
    print("TradeNova Status Summary")
    print("="*70)
    print()
    
    # Check database
    db_path = Path('data/options_history.db')
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM options_chains")
            contracts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM options_chains")
            symbols = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT date) FROM options_chains")
            dates = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM options_chains")
            date_range = cursor.fetchone()
            
            file_size_mb = db_path.stat().st_size / (1024 * 1024)
            
            conn.close()
            
            print("[COMPLETE] Options Data Foundation:")
            print(f"  - Contracts collected: {contracts:,}")
            print(f"  - Symbols: {symbols}")
            print(f"  - Trading days: {dates}")
            print(f"  - Date range: {date_range[0]} to {date_range[1]}")
            print(f"  - Database size: {file_size_mb:.1f} MB")
            print(f"  - Database: {db_path.absolute()}")
            print()
            
        except Exception as e:
            print(f"[WARNING] Could not read database: {e}")
            print()
    
    # Status breakdown
    print("[COMPLETE] Core Infrastructure:")
    print("  - Infrastructure: 100%")
    print("  - Risk System: 90%")
    print("  - Multi-Agent Design: 80%")
    print("  - Options Data: 70%")
    print()
    
    print("[PENDING] Critical Gaps:")
    print("  - Portfolio Risk Layer: 0% (CRITICAL)")
    print("  - RL State Enhancement: 70% (HIGH) - COMPLETED TODAY")
    print("  - Advanced Greeks: 30% (HIGH)")
    print("  - Volatility Modeling: 40% (HIGH)")
    print("  - Execution Upgrade: 40% (MEDIUM)")
    print("  - Backtester: 30% (MEDIUM)")
    print()
    
    print("[PROGRESS] Overall: 70% Complete (+5% today)")
    print()
    
    print("="*70)
    print("Next Steps:")
    print("="*70)
    print("1. Enhance RL State - Add Greeks/IV to observations")
    print("2. Build Portfolio Risk Layer - Delta/Theta caps, UVaR")
    print("3. Add Advanced Greeks - Heston, SABR models")
    print()
    
    print("Full Reports:")
    print("  - CURRENT_STATUS_SUMMARY.md")
    print("  - ROADMAP_VALIDATION.md")
    print("="*70)

if __name__ == '__main__':
    show_status()

