#!/usr/bin/env python3
"""
Basic test to validate the project structure without external dependencies
"""

import os
import sys
from datetime import datetime

def test_directory_structure():
    """Test that all required directories exist"""
    required_dirs = [
        "models",
        "nodes", 
        "prompts",
        "utils",
        "data/users/alex/plans"
    ]
    
    print("Testing directory structure...")
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path} exists")
        else:
            print(f"❌ {dir_path} missing")
            return False
    return True

def test_file_structure():
    """Test that all required files exist"""
    required_files = [
        "models/user.py",
        "models/agent_state.py",
        "nodes/planning.py",
        "nodes/checkins.py", 
        "nodes/interrupts.py",
        "prompts/system_prompt.py",
        "prompts/phase_prompts.py",
        "utils/telegram_bot.py",
        "main.py",
        ".env"
    ]
    
    print("\nTesting file structure...")
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    return True

def test_env_variables():
    """Test that environment variables are set"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "TELEGRAM_TOKEN",
        "OPENAI_API_KEY", 
        "TELEGRAM_CHAT_ID",
        "TAVILY_API_KEY"
    ]
    
    print("\nTesting environment variables...")
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} not set")
            return False
    return True

def main():
    print("🚀 Starting basic project validation...\n")
    
    tests = [
        test_directory_structure,
        test_file_structure,
        test_env_variables
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 All basic validation tests passed!")
        print("Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run the main application: python3 main.py")
    else:
        print("❌ Some tests failed. Please check the output above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())