#!/usr/bin/env python3
"""
Test script to verify the bot setup and configuration.
"""

import yaml
import sys
import os
from datetime import datetime


def test_config():
    """Test if config.yaml is properly set up."""
    print("Testing configuration...")
    
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # Check required fields
        required_fields = ["bot_token", "providers", "models", "system_prompt"]
        missing = []
        
        for field in required_fields:
            if field not in config:
                missing.append(field)
        
        if missing:
            print(f"❌ Missing required fields: {missing}")
            return False
        
        # Check if OpenRouter is configured
        if "openrouter" not in config.get("providers", {}):
            print("❌ OpenRouter provider not configured")
            return False
        
        # Check if API key is set
        api_key = config["providers"]["openrouter"].get("api_key", "")
        if not api_key or api_key == "${{ OPENROUTER_API_KEY }}":
            print("❌ OpenRouter API key not set. Set OPENROUTER_API_KEY environment variable.")
            return False
        
        # Check bot token
        bot_token = config.get("bot_token", "")
        if not bot_token or bot_token == "${{ BOT_TOKEN }}":
            print("❌ Bot token not set. Set BOT_TOKEN environment variable.")
            return False
        
        print("✅ Configuration looks good!")
        print(f"   - Models available: {len(config.get('models', {}))}")
        print(f"   - Tools enabled: {config.get('enable_tools', False)}")
        print(f"   - Plain responses: {config.get('use_plain_responses', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False


def test_imports():
    """Test if all required modules can be imported."""
    print("\nTesting imports...")
    
    modules = [
        "discord",
        "openai",
        "httpx",
        "yaml",
        "tools",
        "formatters"
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed.append(module)
    
    return len(failed) == 0


def test_environment():
    """Test environment setup."""
    print("\nTesting environment...")
    
    required_env = ["BOT_TOKEN", "OPENROUTER_API_KEY"]
    missing = []
    
    for var in required_env:
        if not os.getenv(var):
            missing.append(var)
            print(f"❌ Missing environment variable: {var}")
        else:
            print(f"✅ {var} is set")
    
    if missing:
        print("\nSet missing environment variables:")
        for var in missing:
            print(f"  export {var}='your-{var.lower()}'")
        return False
    
    return True


def main():
    """Run all tests."""
    print("🤖 LLMCord Bot Test Suite")
    print("=" * 40)
    
    tests = [
        test_config,
        test_imports,
        test_environment
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All tests passed! Your bot is ready to run.")
        print("\nTo start the bot, run:")
        print("  python llmcord.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()