#!/usr/bin/env python3
"""
Quick validation script to ensure the assistant is set up correctly
"""
import os
import sys
import asyncio
from pathlib import Path


def check_environment_variables():
    """Check required environment variables"""
    print("🔐 Checking environment variables...")
    
    required_vars = [
        "TELEGRAM_TOKEN",
        "OPENAI_API_KEY", 
        "TELEGRAM_CHAT_ID",
        "TAVILY_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All environment variables present")
        return True


def check_file_structure():
    """Check project file structure"""
    print("\n📁 Checking file structure...")
    
    required_files = [
        ".env",
        "main.py",
        "models/user.py",
        "models/agent_state.py",
        "utils/telegram_bot.py",
        "utils/google_calendar.py",
        "data/users/alex"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files/directories: {', '.join(missing_files)}")
        return False
    else:
        print("✅ All required files present")
        return True


def check_google_calendar_setup():
    """Check Google Calendar setup"""
    print("\n📅 Checking Google Calendar setup...")
    
    credentials_path = "data/users/alex/google_credentials.json"
    
    if Path(credentials_path).exists():
        print("✅ Google Calendar credentials file found")
        
        # Try to initialize calendar manager
        try:
            from utils.google_calendar import GoogleCalendarManager
            manager = GoogleCalendarManager("alex")
            
            if manager.is_available():
                print("✅ Google Calendar is properly configured and accessible")
                return True
            else:
                print("⚠️  Google Calendar credentials found but not authorized yet")
                print("   Use /calendar command in Telegram to complete authorization")
                return True
        except Exception as e:
            print(f"❌ Error initializing Google Calendar: {e}")
            return False
    else:
        print("⚠️  Google Calendar not set up (optional)")
        print(f"   To set up: save OAuth credentials to {credentials_path}")
        return True


def test_basic_imports():
    """Test that all modules can be imported"""
    print("\n📦 Testing module imports...")
    
    modules_to_test = [
        "models.user",
        "models.agent_state", 
        "utils.telegram_bot",
        "utils.google_calendar",
        "utils.scheduler",
        "nodes.planning",
        "nodes.checkins",
        "nodes.interrupts",
        "prompts.system_prompt",
        "prompts.phase_prompts"
    ]
    
    failed_imports = []
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        return False
    else:
        print("✅ All modules imported successfully")
        return True


def test_user_creation():
    """Test user creation functionality"""
    print("\n👤 Testing user creation...")
    
    try:
        from models.user import User
        user = User.load_or_create("test_validation_user")
        
        assert user.profile.user_id == "test_validation_user"
        assert user.profile.name == "Alex"
        print("✅ User creation works correctly")
        return True
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        return False


def test_agent_state():
    """Test agent state functionality"""
    print("\n🤖 Testing agent state...")
    
    try:
        from models.agent_state import create_initial_state
        state = create_initial_state("test_user")
        
        assert state["current_phase"] == "morning_planning"
        assert state["user_context"]["user_id"] == "test_user"
        print("✅ Agent state creation works correctly")
        return True
    except Exception as e:
        print(f"❌ Agent state creation failed: {e}")
        return False


async def test_telegram_bot_init():
    """Test Telegram bot initialization"""
    print("\n📱 Testing Telegram bot initialization...")
    
    try:
        from utils.telegram_bot import TelegramBotInterface
        bot = TelegramBotInterface()
        
        assert bot.token is not None
        assert bot.chat_id is not None
        print("✅ Telegram bot initializes correctly")
        return True
    except Exception as e:
        print(f"❌ Telegram bot initialization failed: {e}")
        return False


def test_scheduler_functionality():
    """Test scheduler functionality"""
    print("\n⏰ Testing scheduler functionality...")
    
    try:
        from utils.scheduler import DailyScheduler, SchedulerState, create_scheduler_for_user
        from datetime import time
        from unittest.mock import patch
        
        # Test scheduler creation
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            scheduler = create_scheduler_for_user("test_user")
            assert scheduler.user_id == "test_user"
        
        # Test schedule manipulation
        scheduler.update_schedule("morning_planning", time(6, 30))
        assert scheduler.schedule["morning_planning"] == time(6, 30)
        
        # Test phase progression
        assert scheduler.get_next_phase("morning_planning") == "morning_checkin"
        assert scheduler.get_next_phase("nighttime_planning") == "morning_planning"
        
        print("✅ Scheduler functionality works correctly")
        return True
    except Exception as e:
        print(f"❌ Scheduler functionality test failed: {e}")
        return False


async def main():
    """Run all validation checks"""
    print("🧪 Personal AI Assistant - Setup Validation")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    checks = [
        check_environment_variables(),
        check_file_structure(),
        test_basic_imports(),
        test_user_creation(),
        test_agent_state(),
        await test_telegram_bot_init(),
        test_scheduler_functionality(),
        check_google_calendar_setup()
    ]
    
    passed_checks = sum(checks)
    total_checks = len(checks)
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Results: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 All validation checks passed! The assistant is ready to use.")
        print("\nTo start the assistant:")
        print("  ./start.sh")
        return 0
    else:
        print("⚠️  Some validation checks failed. Please address the issues above.")
        print("\nFor help:")
        print("  python3 run_tests.py --help")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))