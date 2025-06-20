"""
Shared test configuration and fixtures
"""
import pytest
import asyncio
import tempfile
import shutil
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from freezegun import freeze_time

# Import our modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.user import User, UserProfile, DailyPlan
from models.agent_state import AgentState, create_initial_state
from utils.google_calendar import GoogleCalendarManager


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    test_user_dir = os.path.join(temp_dir, "users", "test_user")
    os.makedirs(test_user_dir, exist_ok=True)
    os.makedirs(os.path.join(test_user_dir, "plans"), exist_ok=True)
    
    # Patch the data directory paths
    with patch('models.user.User._ensure_user_directory'):
        with patch('models.user.User._save_profile'):
            yield test_user_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing"""
    return UserProfile.create_default("test_user")


@pytest.fixture
def sample_daily_plan():
    """Create a sample daily plan for testing"""
    return DailyPlan.create(
        "Today let's focus on gentle awareness and taking breaks.",
        "test_source"
    )


@pytest.fixture
def sample_agent_state():
    """Create a sample agent state for testing"""
    return create_initial_state("test_user")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response from AI"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_calendar_events():
    """Sample calendar events for testing"""
    now = datetime.now()
    return [
        {
            'id': 'event1',
            'summary': 'Morning Meeting',
            'description': 'Team standup',
            'start_time': now.replace(hour=9, minute=0),
            'end_time': now.replace(hour=10, minute=0),
            'is_all_day': False,
            'location': 'Conference Room A',
            'status': 'confirmed',
            'url': 'https://calendar.google.com/event1',
            'duration_minutes': 60
        },
        {
            'id': 'event2',
            'summary': 'Lunch Break',
            'description': '',
            'start_time': now.replace(hour=12, minute=0),
            'end_time': now.replace(hour=13, minute=0),
            'is_all_day': False,
            'location': '',
            'status': 'confirmed',
            'url': 'https://calendar.google.com/event2',
            'duration_minutes': 60
        },
        {
            'id': 'event3',
            'summary': 'All Day Event',
            'description': 'Conference day',
            'start_time': now.replace(hour=0, minute=0),
            'end_time': now.replace(hour=23, minute=59),
            'is_all_day': True,
            'location': 'Convention Center',
            'status': 'confirmed',
            'url': 'https://calendar.google.com/event3',
            'duration_minutes': None
        }
    ]


@pytest.fixture
def mock_calendar_manager(mock_calendar_events):
    """Mock Google Calendar manager"""
    mock_manager = Mock(spec=GoogleCalendarManager)
    mock_manager.is_available.return_value = True
    mock_manager.get_todays_events.return_value = mock_calendar_events
    mock_manager.get_upcoming_events.return_value = mock_calendar_events
    mock_manager.get_next_event.return_value = mock_calendar_events[0]
    mock_manager.format_events_for_display.return_value = "• 09:00 - 10:00: Morning Meeting (Conference Room A)\n• 12:00 - 13:00: Lunch Break\n• All day: All Day Event (Convention Center)"
    mock_manager.get_calendar_context_for_planning.return_value = {
        'has_calendar_access': True,
        'today_events_count': 3,
        'today_events': mock_calendar_events,
        'next_event': mock_calendar_events[0],
        'calendar_summary': "• 09:00 - 10:00: Morning Meeting (Conference Room A)\n• 12:00 - 13:00: Lunch Break\n• All day: All Day Event (Convention Center)"
    }
    return mock_manager


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update object"""
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.text = "Test message"
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123456789
    return mock_update


@pytest.fixture
def mock_telegram_context():
    """Mock Telegram context object"""
    return Mock()


# Utility functions for tests
def assert_agent_state_valid(state: AgentState):
    """Assert that an agent state is valid"""
    assert "messages" in state
    assert "user_context" in state
    assert "current_phase" in state
    assert "interrupt_flag" in state
    assert state["user_context"]["user_id"] is not None
    assert state["current_phase"] in [
        "morning_planning", "morning_checkin", "midday_checkin", 
        "evening_checkin", "nighttime_planning"
    ]


def create_test_calendar_event(summary: str, start_hour: int, duration_minutes: int = 60, is_all_day: bool = False):
    """Create a test calendar event"""
    now = datetime.now()
    start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    return {
        'id': f'test_{summary.lower().replace(" ", "_")}',
        'summary': summary,
        'description': f'Test event: {summary}',
        'start_time': start_time,
        'end_time': end_time,
        'is_all_day': is_all_day,
        'location': 'Test Location',
        'status': 'confirmed',
        'url': f'https://calendar.google.com/{summary}',
        'duration_minutes': duration_minutes if not is_all_day else None
    }