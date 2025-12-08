"""
Setup Verification Script for TradeNova
Run this to verify your installation and configuration
"""
import sys
import os

def check_dependencies():
    """Check if all required packages are installed"""
    print("Checking dependencies...")
    required_packages = [
        'alpaca_trade_api',
        'pandas',
        'numpy',
        'dotenv',
        'schedule',
        'colorama'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            elif package == 'alpaca_trade_api':
                __import__('alpaca_trade_api')
            else:
                __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\nChecking environment configuration...")
    
    if not os.path.exists('.env'):
        print("  ✗ .env file not found")
        print("  Create .env from .env.example and add your Alpaca API credentials")
        return False
    
    print("  ✓ .env file exists")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY']
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f'your_{var.lower()}_here':
            print(f"  ✗ {var} not set")
            missing.append(var)
        else:
            print(f"  ✓ {var} is set")
    
    if missing:
        print(f"\nPlease set the following in .env: {', '.join(missing)}")
        return False
    
    return True

def check_config():
    """Check if configuration loads correctly"""
    print("\nChecking configuration...")
    try:
        from config import Config
        Config.validate()
        print("  ✓ Configuration loaded successfully")
        print(f"  ✓ Tickers: {len(Config.TICKERS)} configured")
        print(f"  ✓ Max Active Trades: {Config.MAX_ACTIVE_TRADES}")
        print(f"  ✓ Position Size: {Config.POSITION_SIZE_PCT*100}%")
        print(f"  ✓ Stop Loss: {Config.STOP_LOSS_PCT*100}%")
        return True
    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        return False

def check_alpaca_connection():
    """Check if Alpaca API connection works"""
    print("\nChecking Alpaca API connection...")
    try:
        from config import Config
        from alpaca_client import AlpacaClient
        
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        account = client.get_account()
        print(f"  ✓ Connected to Alpaca")
        print(f"  ✓ Account Equity: ${float(account['equity']):,.2f}")
        print(f"  ✓ Cash: ${float(account['cash']):,.2f}")
        print(f"  ✓ Market Open: {client.is_market_open()}")
        return True
    except Exception as e:
        print(f"  ✗ Connection error: {e}")
        print("  Check your API credentials in .env")
        return False

def main():
    """Run all checks"""
    print("="*60)
    print("TRADENOVA SETUP VERIFICATION")
    print("="*60)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_env_file),
        ("Configuration", check_config),
        ("Alpaca Connection", check_alpaca_connection)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ✗ Error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {name}: {status}")
        if not result:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✓ All checks passed! TradeNova is ready to use.")
        print("Run: python main.py")
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()


