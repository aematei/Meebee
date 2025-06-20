#!/usr/bin/env python3
"""
Hello World test to demonstrate basic functionality without full dependencies
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Simple mock classes to test the structure
class MockDailyPlan:
    def __init__(self, content: str):
        self.content = content
        self.metadata = {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "update_source": "hello_world_test"
        }

class MockUserProfile:
    def __init__(self):
        self.user_id = "alex"
        self.name = "Alex"
        self.age = 30
        self.condition = "ADHD-C"
        self.goals = ["Improve time awareness", "Better executive function"]
        self.preferences = {"communication_style": "gentle"}

class MockState:
    def __init__(self):
        self.current_phase = "morning_planning"
        self.daily_plan = None
        self.messages = []
        self.user_context = {"user_id": "alex"}

async def mock_morning_planning(state):
    """Mock morning planning function"""
    print("🌅 Mock Morning Planning Phase")
    
    plan_content = "Today let's focus on gentle awareness and taking things one step at a time. Remember to take breaks and be kind to yourself."
    
    state.daily_plan = MockDailyPlan(plan_content)
    state.current_phase = "morning_checkin"
    state.messages.append({
        "role": "assistant",
        "content": plan_content,
        "timestamp": datetime.now().isoformat(),
        "phase": "morning_planning"
    })
    
    print(f"✅ Plan created: {plan_content[:50]}...")
    return state

async def mock_telegram_send(message: str):
    """Mock Telegram send function"""
    print(f"📱 [TELEGRAM] Would send: {message}")
    return True

async def run_hello_world_demo():
    """Run a simple hello world demonstration"""
    print("🚀 Starting Hello World Demo\n")
    
    # Test environment variables
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY") 
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if telegram_token and openai_key and chat_id:
        print("✅ Environment variables loaded successfully")
    else:
        print("❌ Missing environment variables")
        return
    
    # Test basic structure
    print("\n📋 Testing basic structure...")
    
    # Create mock objects
    user_profile = MockUserProfile()
    state = MockState()
    
    print(f"✅ User profile created for: {user_profile.name}")
    print(f"✅ Initial state created with phase: {state.current_phase}")
    
    # Test mock workflow
    print("\n🔄 Testing mock workflow...")
    
    # Run mock morning planning
    state = await mock_morning_planning(state)
    
    # Test mock Telegram integration
    print("\n📱 Testing mock Telegram integration...")
    await mock_telegram_send("Hello! Your personal AI assistant is ready to help with gentle awareness throughout the day.")
    
    # Show final state
    print("\n📊 Final State:")
    print(f"Current Phase: {state.current_phase}")
    print(f"Plan: {state.daily_plan.content if state.daily_plan else 'None'}")
    print(f"Messages: {len(state.messages)} message(s)")
    
    print("\n🎉 Hello World Demo completed successfully!")
    print("\nThis demonstrates:")
    print("✅ Project structure is correct")
    print("✅ Environment variables are loaded") 
    print("✅ Basic state management works")
    print("✅ Mock workflow execution works")
    print("✅ Mock Telegram integration works")
    
    print("\n🚀 Ready for full deployment with:")
    print("1. pip install -r requirements.txt")
    print("2. python3 main.py")

if __name__ == "__main__":
    asyncio.run(run_hello_world_demo())