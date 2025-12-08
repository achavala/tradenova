#!/usr/bin/env python3
"""
Quick Validation Script
Runs a quick validation check of all system components
"""
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_imports():
    """Check all critical imports"""
    logger.info("Checking imports...")
    
    try:
        from alpaca_client import AlpacaClient
        from config import Config
        from core.multi_agent_orchestrator import MultiAgentOrchestrator
        from core.live.integrated_trader import IntegratedTrader
        from core.live.broker_executor import BrokerExecutor
        from core.risk.advanced_risk_manager import AdvancedRiskManager
        from core.risk.profit_manager import ProfitManager
        from core.live.model_degrade_detector import ModelDegradeDetector
        from core.live.ensemble_predictor import EnsemblePredictor
        from core.live.news_filter import NewsFilter
        from core.live.signal_capture import SignalCapture
        from rl.predict import RLPredictor
        from rl.trading_environment import TradingEnvironment
        from logs.metrics_tracker import MetricsTracker
        logger.info("✅ All imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        return False

def check_config():
    """Check configuration"""
    logger.info("Checking configuration...")
    
    try:
        from config import Config
        Config.validate()
        logger.info("✅ Configuration valid")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("   Please check your .env file")
        return False

def check_directories():
    """Check required directories"""
    logger.info("Checking directories...")
    
    dirs = ['logs', 'models', 'logs/signals', 'logs/tensorboard']
    all_exist = True
    
    for dir_path in dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created directory: {dir_path}")
        else:
            logger.info(f"✅ Directory exists: {dir_path}")
    
    return True

def check_components():
    """Check component initialization"""
    logger.info("Checking components...")
    
    try:
        # Check ensemble predictor
        from core.live.ensemble_predictor import EnsemblePredictor
        ensemble = EnsemblePredictor()
        logger.info("✅ Ensemble predictor initialized")
        
        # Check model degrade detector
        from core.live.model_degrade_detector import ModelDegradeDetector
        detector = ModelDegradeDetector()
        logger.info("✅ Model degrade detector initialized")
        
        # Check news filter
        from core.live.news_filter import NewsFilter
        news_filter = NewsFilter()
        logger.info("✅ News filter initialized")
        
        # Check signal capture
        from core.live.signal_capture import SignalCapture
        capture = SignalCapture()
        logger.info("✅ Signal capture initialized")
        
        return True
    except Exception as e:
        logger.error(f"❌ Component initialization error: {e}")
        return False

def check_models():
    """Check for trained models"""
    logger.info("Checking for trained models...")
    
    models_dir = Path("models")
    if not models_dir.exists():
        logger.warning("⚠️  Models directory doesn't exist")
        return False
    
    models = list(models_dir.glob("*.zip"))
    if not models:
        logger.warning("⚠️  No trained models found")
        logger.info("   Train a model with: python rl/train_rl.py --agent grpo --symbol SPY --timesteps 10000")
        return False
    
    logger.info(f"✅ Found {len(models)} model(s):")
    for model in models:
        logger.info(f"   - {model.name}")
    
    return True

def main():
    """Run all validation checks"""
    logger.info("="*60)
    logger.info("TRADENOVA QUICK VALIDATION")
    logger.info("="*60)
    logger.info("")
    
    checks = [
        ("Imports", check_imports),
        ("Configuration", check_config),
        ("Directories", check_directories),
        ("Components", check_components),
        ("Models", check_models),
    ]
    
    results = []
    for name, check_func in checks:
        logger.info(f"\n[{name}]")
        result = check_func()
        results.append((name, result))
    
    logger.info("\n" + "="*60)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("")
    logger.info(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("")
        logger.info("🎉 All checks passed! System is ready for validation.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run dry-run: python run_daily.py --dry-run")
        logger.info("  2. Run paper trading: python run_daily.py --paper")
        logger.info("  3. View dashboard: streamlit run dashboard.py")
        return 0
    else:
        logger.info("")
        logger.warning("⚠️  Some checks failed. Please fix issues before proceeding.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

