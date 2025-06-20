"""
Integration tests for LangGraph workflow
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from freezegun import freeze_time

from models.agent_state import create_initial_state
from nodes.planning import morning_planning, nighttime_planning
from nodes.checkins import morning_checkin, midday_checkin, evening_checkin
from nodes.interrupts import handle_interrupt, should_interrupt


@pytest.mark.integration
class TestWorkflowNodes:
    """Test individual workflow nodes"""
    
    @patch('nodes.planning.create_google_calendar_manager')
    @patch('nodes.planning.User.load_or_create')
    @patch('nodes.planning.client')
    @pytest.mark.asyncio
    async def test_morning_planning_node(self, mock_client, mock_user, mock_calendar_manager_func, 
                                       sample_user_profile, mock_calendar_manager, mock_openai_client):
        """Test morning planning node"""
        # Setup mocks
        mock_user.return_value = Mock(profile=sample_user_profile)
        mock_calendar_manager_func.return_value = mock_calendar_manager
        mock_client.chat.completions.create = mock_openai_client.chat.completions.create
        
        # Create initial state
        state = create_initial_state("test_user")
        
        # Run morning planning
        result_state = await morning_planning(state)
        
        # Verify state changes
        assert result_state["current_phase"] == "morning_checkin"
        assert result_state["daily_plan"] is not None
        assert result_state["daily_plan"]["content"] == "Test response from AI"
        assert len(result_state["messages"]) == 1
        assert result_state["messages"][0]["role"] == "assistant"
        assert result_state["messages"][0]["phase"] == "morning_planning"
    
    @patch('nodes.checkins.create_google_calendar_manager')
    @patch('nodes.checkins.User.load_or_create')
    @patch('nodes.checkins.client')
    @pytest.mark.asyncio
    async def test_midday_checkin_node(self, mock_client, mock_user, mock_calendar_manager_func,
                                     sample_user_profile, mock_calendar_manager, mock_openai_client):
        """Test midday check-in node"""
        # Setup mocks
        mock_user.return_value = Mock(profile=sample_user_profile)
        mock_calendar_manager_func.return_value = mock_calendar_manager
        mock_client.chat.completions.create = mock_openai_client.chat.completions.create
        
        # Create state with existing plan
        state = create_initial_state("test_user")
        state["daily_plan"] = {
            "content": "Today's plan",
            "metadata": {"created": datetime.now().isoformat()}
        }
        state["current_phase"] = "midday_checkin"
        
        # Run midday check-in
        result_state = await midday_checkin(state)
        
        # Verify state changes
        assert result_state["current_phase"] == "evening_checkin"
        assert "next_event" in result_state["context_data"]
        assert len(result_state["messages"]) == 1
        assert result_state["messages"][0]["phase"] == "midday_checkin"
    
    @patch('nodes.planning.User.load_or_create')
    @patch('nodes.planning.client')
    @pytest.mark.asyncio
    async def test_nighttime_planning_node(self, mock_client, mock_user, 
                                         sample_user_profile, mock_openai_client):
        """Test nighttime planning node"""
        # Setup mocks
        mock_user_instance = Mock(profile=sample_user_profile)
        mock_user_instance.archive_current_plan = Mock()
        mock_user_instance.save = Mock()
        mock_user.return_value = mock_user_instance
        mock_client.chat.completions.create = mock_openai_client.chat.completions.create
        
        # Create state with existing plan
        state = create_initial_state("test_user")
        state["daily_plan"] = {
            "content": "Today's completed plan",
            "metadata": {"created": datetime.now().isoformat()}
        }
        state["current_phase"] = "nighttime_planning"
        
        # Run nighttime planning
        result_state = await nighttime_planning(state)
        
        # Verify state changes
        assert result_state["current_phase"] == "morning_planning"  # Reset for next day
        assert result_state["daily_plan"] is None  # Cleared for fresh start
        assert len(result_state["messages"]) == 1
        assert result_state["messages"][0]["phase"] == "nighttime_planning"
        
        # Verify user methods were called
        mock_user_instance.archive_current_plan.assert_called_once()
        mock_user_instance.save.assert_called_once()


@pytest.mark.integration
class TestInterruptHandling:
    """Test interrupt handling functionality"""
    
    @patch('nodes.interrupts.User.load_or_create')
    @patch('nodes.interrupts.client')
    @pytest.mark.asyncio
    async def test_handle_interrupt(self, mock_client, mock_user, 
                                  sample_user_profile, mock_openai_client):
        """Test interrupt handling"""
        # Setup mocks
        mock_user.return_value = Mock(profile=sample_user_profile)
        mock_client.chat.completions.create = mock_openai_client.chat.completions.create
        
        # Create state
        state = create_initial_state("test_user")
        state["current_phase"] = "morning_checkin"
        
        # Handle interrupt
        user_message = "I'm feeling overwhelmed right now"
        result_state = await handle_interrupt(state, user_message)
        
        # Verify interrupt context is saved
        assert result_state["user_context"]["interrupt_context"] is not None
        assert result_state["user_context"]["interrupt_context"]["interrupted_phase"] == "morning_checkin"
        assert result_state["user_context"]["interrupt_context"]["message"] == user_message
        
        # Verify messages were added
        assert len(result_state["messages"]) == 2  # User message + assistant response
        assert result_state["messages"][0]["role"] == "user"
        assert result_state["messages"][0]["interrupt"] is True
        assert result_state["messages"][1]["role"] == "assistant"
        assert result_state["messages"][1]["interrupt"] is True
    
    def test_should_interrupt_urgent_keywords(self):
        """Test interrupt detection with urgent keywords"""
        state = create_initial_state("test_user")
        
        urgent_messages = [
            "I need help right now",
            "I'm feeling overwhelmed",
            "This is urgent",
            "I'm stuck on this task",
            "Having anxiety about the meeting"
        ]
        
        for message in urgent_messages:
            assert should_interrupt(state, message) is True
    
    def test_should_interrupt_during_checkins(self):
        """Test interrupt detection during check-in phases"""
        state = create_initial_state("test_user")
        
        checkin_phases = ["morning_checkin", "midday_checkin", "evening_checkin"]
        
        for phase in checkin_phases:
            state["current_phase"] = phase
            assert should_interrupt(state, "How's the weather?") is True
    
    def test_should_interrupt_default_behavior(self):
        """Test default interrupt behavior"""
        state = create_initial_state("test_user")
        state["current_phase"] = "morning_planning"
        
        # Default is to allow interruptions for flexibility
        assert should_interrupt(state, "Random question") is True


@pytest.mark.integration
class TestWorkflowStateTransitions:
    """Test complete workflow state transitions"""
    
    @freeze_time("2024-01-15 08:00:00")
    @pytest.mark.asyncio
    async def test_complete_daily_cycle_simulation(self, mock_openai_client):
        """Test a complete daily cycle simulation"""
        with patch('nodes.planning.client', mock_openai_client), \
             patch('nodes.checkins.client', mock_openai_client), \
             patch('nodes.planning.User.load_or_create') as mock_user_planning, \
             patch('nodes.checkins.User.load_or_create') as mock_user_checkins, \
             patch('nodes.planning.create_google_calendar_manager') as mock_cal_planning, \
             patch('nodes.checkins.create_google_calendar_manager') as mock_cal_checkins:
            
            # Setup common mocks
            mock_profile = Mock()
            mock_profile.user_id = "test_user"
            mock_profile.name = "Alex"
            mock_profile.age = 30
            mock_profile.condition = "ADHD-C"
            mock_profile.goals = ["Improve time awareness", "Better executive function"]
            mock_profile.preferences = {"communication_style": "gentle", "focus_areas": ["time_awareness"]}
            
            mock_user = Mock(profile=mock_profile)
            mock_user.update_plan = Mock()
            mock_user.save = Mock()
            mock_user.archive_current_plan = Mock()
            
            mock_user_planning.return_value = mock_user
            mock_user_checkins.return_value = mock_user
            
            # Setup calendar manager
            mock_calendar_manager = Mock()
            mock_calendar_manager.get_calendar_context_for_planning.return_value = {
                'has_calendar_access': True,
                'today_events_count': 0,
                'today_events': [],
                'next_event': None,
                'calendar_summary': "No events today"
            }
            mock_calendar_manager.get_next_event.return_value = None
            mock_cal_planning.return_value = mock_calendar_manager
            mock_cal_checkins.return_value = mock_calendar_manager
            
            # Start with initial state
            state = create_initial_state("test_user")
            
            # Morning planning
            state = await morning_planning(state)
            assert state["current_phase"] == "morning_checkin"
            assert state["daily_plan"] is not None
            
            # Morning check-in
            state = await morning_checkin(state)
            assert state["current_phase"] == "midday_checkin"
            
            # Midday check-in
            state = await midday_checkin(state)
            assert state["current_phase"] == "evening_checkin"
            
            # Evening check-in
            state = await evening_checkin(state)
            assert state["current_phase"] == "nighttime_planning"
            
            # Nighttime planning
            with patch('nodes.planning.User.load_or_create', return_value=mock_user):
                state = await nighttime_planning(state)
            
            assert state["current_phase"] == "morning_planning"  # Cycle complete
            assert state["daily_plan"] is None  # Reset for next day
            
            # Verify all phases generated messages
            phase_messages = [msg["phase"] for msg in state["messages"] if "phase" in msg]
            expected_phases = ["morning_planning", "morning_checkin", "midday_checkin", 
                             "evening_checkin", "nighttime_planning"]
            assert all(phase in phase_messages for phase in expected_phases)


@pytest.mark.integration
class TestWorkflowWithCalendar:
    """Test workflow integration with calendar events"""
    
    @patch('nodes.planning.create_google_calendar_manager')
    @patch('nodes.planning.User.load_or_create')
    @patch('nodes.planning.client')
    @pytest.mark.asyncio
    async def test_morning_planning_with_events(self, mock_client, mock_user, mock_calendar_manager,
                                              sample_user_profile, mock_calendar_events, mock_openai_client):
        """Test morning planning with calendar events"""
        # Setup mocks
        mock_user.return_value = Mock(profile=sample_user_profile)
        calendar_manager = Mock()
        calendar_manager.get_calendar_context_for_planning.return_value = {
            'has_calendar_access': True,
            'today_events_count': 3,
            'today_events': mock_calendar_events,
            'next_event': mock_calendar_events[0],
            'calendar_summary': "• 09:00 - 10:00: Morning Meeting\n• 12:00 - 13:00: Lunch"
        }
        mock_calendar_manager.return_value = calendar_manager
        mock_client.chat.completions.create = mock_openai_client.chat.completions.create
        
        # Create initial state
        state = create_initial_state("test_user")
        
        # Run morning planning
        result_state = await morning_planning(state)
        
        # Verify calendar context was added to state
        assert "today_events" in result_state["context_data"]
        assert result_state["context_data"]["today_events_count"] == 3
        assert result_state["context_data"]["has_calendar_access"] is True
        
        # Verify OpenAI was called with calendar info
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "Today's calendar:" in user_message