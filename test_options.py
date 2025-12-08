#!/usr/bin/env python3
"""
Test script for options infrastructure
"""
import sys

print("Testing options infrastructure imports...")
print("-" * 50)

try:
    from services.options_data_feed import OptionsDataFeed
    print("✅ OptionsDataFeed imported successfully")
except ImportError as e:
    print(f"❌ Failed to import OptionsDataFeed: {e}")
    sys.exit(1)

try:
    from services.iv_calculator import IVCalculator
    print("✅ IVCalculator imported successfully")
except ImportError as e:
    print(f"❌ Failed to import IVCalculator: {e}")
    sys.exit(1)

try:
    from services.gex_calculator import GEXCalculator
    print("✅ GEXCalculator imported successfully")
except ImportError as e:
    print(f"❌ Failed to import GEXCalculator: {e}")
    sys.exit(1)

try:
    from core.live.options_broker_client import OptionsBrokerClient
    print("✅ OptionsBrokerClient imported successfully")
except ImportError as e:
    print(f"❌ Failed to import OptionsBrokerClient: {e}")
    sys.exit(1)

try:
    from core.agents.options_agent import OptionsAgent
    print("✅ OptionsAgent imported successfully")
except ImportError as e:
    print(f"❌ Failed to import OptionsAgent: {e}")
    sys.exit(1)

try:
    from core.agents.theta_harvester_agent import ThetaHarvesterAgent
    print("✅ ThetaHarvesterAgent imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ThetaHarvesterAgent: {e}")
    sys.exit(1)

try:
    from core.agents.gamma_scalper_agent import GammaScalperAgent
    print("✅ GammaScalperAgent imported successfully")
except ImportError as e:
    print(f"❌ Failed to import GammaScalperAgent: {e}")
    sys.exit(1)

try:
    from core.multi_agent_orchestrator import MultiAgentOrchestrator
    print("✅ MultiAgentOrchestrator imported successfully")
except ImportError as e:
    print(f"❌ Failed to import MultiAgentOrchestrator: {e}")
    sys.exit(1)

print("-" * 50)
print("🎉 All options infrastructure imports successful!")
print("\nOptions infrastructure is ready to use!")

