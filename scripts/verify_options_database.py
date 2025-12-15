#!/usr/bin/env python3
"""
Verify Options Database
Check that data is properly stored and persistent
"""
import sys
import sqlite3
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_database():
    """Verify the options database exists and has data"""
    db_path = Path('data/options_history.db')
    
    print("="*60)
    print("Options Database Verification")
    print("="*60)
    print()
    
    # Check if database exists
    if not db_path.exists():
        print("❌ Database file not found!")
        print(f"   Expected: {db_path.absolute()}")
        return 1
    
    file_size = db_path.stat().st_size / (1024 * 1024)  # MB
    print(f"✅ Database file exists: {db_path.absolute()}")
    print(f"✅ File size: {file_size:.2f} MB")
    print()
    
    # Connect to database
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📊 Database Tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count:,} records")
        print()
        
        # Check options_chains data
        if 'options_chains' in tables:
            print("📈 Options Chains Data:")
            
            cursor.execute("SELECT COUNT(*) FROM options_chains")
            total = cursor.fetchone()[0]
            print(f"   - Total contracts: {total:,}")
            
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM options_chains")
            symbols = cursor.fetchone()[0]
            print(f"   - Unique symbols: {symbols}")
            
            cursor.execute("SELECT COUNT(DISTINCT date) FROM options_chains")
            dates = cursor.fetchone()[0]
            print(f"   - Unique dates: {dates}")
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM options_chains")
            date_range = cursor.fetchone()
            print(f"   - Date range: {date_range[0]} to {date_range[1]}")
            
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM options_chains 
                GROUP BY symbol 
                ORDER BY count DESC
            """)
            print()
            print("   Contracts per symbol:")
            for row in cursor.fetchall():
                print(f"     - {row[0]}: {row[1]:,}")
        
        print()
        
        # Check IV history
        if 'iv_history' in tables:
            cursor.execute("SELECT COUNT(*) FROM iv_history")
            iv_count = cursor.fetchone()[0]
            print(f"📊 IV History: {iv_count:,} records")
        
        print()
        print("="*60)
        print("✅ Database verification complete!")
        print("="*60)
        print()
        print("The database is stored on disk and will persist across reboots.")
        print(f"Location: {db_path.absolute()}")
        
        conn.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(verify_database())

