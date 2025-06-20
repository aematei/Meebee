"""
Unit tests for scheduler module
"""
import pytest
import asyncio
import json
from datetime import datetime, time, timedelta
from freezegun import freeze_time
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from utils.scheduler import DailyScheduler, SchedulerState, SchedulerManager


class TestSchedulerState:
    """Test SchedulerState class"""
    
    def test_scheduler_state_initialization(self, temp_data_dir):
        """Test scheduler state creation and default values"""
        with patch('utils.scheduler.Path.mkdir'), \
             patch('utils.scheduler.Path.exists', return_value=False):
            
            state = SchedulerState("test_user")
            
            assert state.user_id == "test_user"
            assert state.get("current_phase") == "morning_planning"
            assert state.get("daily_cycle_count") == 0
            assert state.get("last_phase_transition") is None
            assert isinstance(state.get("last_check_in_times"), dict)
            assert isinstance(state.get("missed_check_ins"), list)
            assert isinstance(state.get("nudge_history"), list)
    
    @patch('utils.scheduler.Path.exists')
    @patch('builtins.open')
    def test_load_existing_state(self, mock_open, mock_exists):
        """Test loading existing scheduler state"""
        # Mock existing state file
        mock_exists.return_value = True
        existing_state = {
            "last_phase_transition": "2024-01-15T10:30:00",
            "current_phase": "midday_checkin",
            "daily_cycle_count": 5,
            "last_check_in_times": {"morning_planning": "2024-01-15T07:00:00"},
            "missed_check_ins": [],
            "nudge_history": []
        }
        
        # Mock file reading
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_file.read.return_value = json.dumps(existing_state)
        mock_open.return_value = mock_file
        
        with patch('json.load', return_value=existing_state), \
             patch('utils.scheduler.Path.mkdir'):
            
            state = SchedulerState("test_user")
            
            assert state.get("current_phase") == "midday_checkin"
            assert state.get("daily_cycle_count") == 5
            assert state.get("last_phase_transition") == "2024-01-15T10:30:00"
    
    @patch('utils.scheduler.Path.mkdir')
    @patch('builtins.open')
    @patch('json.dump')
    def test_save_state(self, mock_json_dump, mock_open, mock_mkdir):
        """Test saving scheduler state"""
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_file
        
        with patch('utils.scheduler.Path.exists', return_value=False):
            state = SchedulerState("test_user")
            state.set("current_phase", "evening_checkin")
        
        # Verify json.dump was called
        mock_json_dump.assert_called()
        call_args = mock_json_dump.call_args
        saved_data = call_args[0][0]
        assert saved_data["current_phase"] == "evening_checkin"


class TestDailyScheduler:
    """Test DailyScheduler class"""
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            assert scheduler.user_id == "test_user"
            assert scheduler.schedule == DailyScheduler.DEFAULT_SCHEDULE
            assert not scheduler.is_running
            assert scheduler.workflow_nodes == {}
    
    def test_custom_schedule_loading(self):
        """Test loading custom user schedule"""
        custom_schedule = {
            "morning_planning": "06:30",
            "morning_checkin": "08:30",
            "midday_checkin": "12:30",
            "evening_checkin": "17:30",
            "nighttime_planning": "20:30"
        }
        
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'), \
             patch('utils.scheduler.Path.exists', return_value=True), \
             patch('builtins.open'), \
             patch('json.load', return_value=custom_schedule):
            
            scheduler = DailyScheduler("test_user")
            
            assert scheduler.schedule["morning_planning"] == time(6, 30)
            assert scheduler.schedule["evening_checkin"] == time(17, 30)
    
    def test_get_next_phase(self):
        """Test phase progression logic"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            assert scheduler.get_next_phase("morning_planning") == "morning_checkin"
            assert scheduler.get_next_phase("midday_checkin") == "evening_checkin"
            assert scheduler.get_next_phase("nighttime_planning") == "morning_planning"
            assert scheduler.get_next_phase("invalid_phase") == "morning_planning"
    
    @freeze_time("2024-01-15 14:30:00")
    def test_get_current_expected_phase(self):
        """Test determining current expected phase based on time"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            # At 14:30, should be in midday_checkin (13:00) but not evening (18:00)
            expected_phase = scheduler.get_current_expected_phase()
            assert expected_phase == "midday_checkin"
    
    @freeze_time("2024-01-15 10:00:00")
    def test_is_check_in_overdue(self):
        """Test overdue check-in detection"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            # Morning planning at 7:00 + 2 hour grace = 9:00 overdue time
            # At 10:00, should be overdue
            assert scheduler.is_check_in_overdue("morning_planning") is True
            
            # Morning checkin at 9:00 + 3 hour grace = 12:00 overdue time
            # At 10:00, should not be overdue
            assert scheduler.is_check_in_overdue("morning_checkin") is False
    
    @freeze_time("2024-01-15 08:30:00")
    def test_get_time_until_next_phase(self):
        """Test calculating time until next phase"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            next_info = scheduler.get_time_until_next_phase()
            
            assert next_info is not None
            assert next_info["phase"] == "morning_checkin"  # Next at 9:00
            assert next_info["minutes_until"] == 30  # 30 minutes from 8:30 to 9:00
    
    @pytest.mark.asyncio
    async def test_send_gentle_nudge(self):
        """Test sending gentle nudges"""
        mock_telegram = AsyncMock()
        mock_state = Mock()
        mock_state.get.return_value = []
        mock_state.set = Mock()
        
        with patch('utils.scheduler.SchedulerState', return_value=mock_state):
            scheduler = DailyScheduler("test_user", mock_telegram)
            
            await scheduler.send_gentle_nudge("morning_checkin", "Time for check-in!")
            
            mock_telegram.send_message.assert_called_once_with("Time for check-in!")
            mock_state.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_phase_transition(self):
        """Test triggering phase transitions"""
        mock_workflow_func = AsyncMock()
        mock_workflow_func.return_value = {"current_phase": "morning_checkin", "messages": []}
        
        mock_state = Mock()
        mock_state.get.return_value = {}
        mock_state.update = Mock()
        mock_state.set = Mock()
        
        with patch('utils.scheduler.SchedulerState', return_value=mock_state), \
             patch('utils.scheduler.TelegramBotInterface'), \
             patch('utils.scheduler.User.load_or_create'), \
             patch('utils.scheduler.create_initial_state'):
            
            scheduler = DailyScheduler("test_user")
            scheduler.set_workflow_nodes({"morning_checkin": mock_workflow_func})
            
            result = await scheduler.trigger_phase_transition("morning_checkin")
            
            assert result is True
            mock_workflow_func.assert_called_once()
            mock_state.update.assert_called()
    
    @pytest.mark.asyncio
    async def test_trigger_phase_transition_no_node(self):
        """Test triggering transition with missing workflow node"""
        mock_state = Mock()
        
        with patch('utils.scheduler.SchedulerState', return_value=mock_state), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            result = await scheduler.trigger_phase_transition("invalid_phase")
            
            assert result is False
    
    def test_update_schedule(self):
        """Test updating schedule times"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'), \
             patch.object(DailyScheduler, '_save_user_schedule'):
            
            scheduler = DailyScheduler("test_user")
            
            new_time = time(8, 30)
            scheduler.update_schedule("morning_planning", new_time)
            
            assert scheduler.schedule["morning_planning"] == new_time
    
    def test_update_schedule_invalid_phase(self):
        """Test updating schedule with invalid phase"""
        with patch('utils.scheduler.SchedulerState'), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            with pytest.raises(ValueError, match="Invalid phase"):
                scheduler.update_schedule("invalid_phase", time(8, 0))
    
    def test_get_schedule_status(self):
        """Test getting schedule status"""
        mock_state = Mock()
        mock_state.get.side_effect = lambda key, default=None: {
            "current_phase": "morning_checkin",
            "last_phase_transition": "2024-01-15T09:00:00",
            "missed_check_ins": []
        }.get(key, default)
        
        with patch('utils.scheduler.SchedulerState', return_value=mock_state), \
             patch('utils.scheduler.TelegramBotInterface'):
            
            scheduler = DailyScheduler("test_user")
            
            status = scheduler.get_schedule_status()
            
            assert status["current_phase"] == "morning_checkin"
            assert "current_time" in status
            assert "schedule" in status
            assert "is_on_schedule" in status


class TestSchedulerManager:
    """Test SchedulerManager class"""
    
    def test_scheduler_manager_initialization(self):
        """Test scheduler manager initialization"""
        manager = SchedulerManager()
        
        assert manager.schedulers == {}
    
    def test_get_scheduler(self):
        """Test getting or creating schedulers"""
        with patch('utils.scheduler.DailyScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler
            
            manager = SchedulerManager()
            scheduler = manager.get_scheduler("test_user")
            
            assert scheduler == mock_scheduler
            assert "test_user" in manager.schedulers
            mock_scheduler_class.assert_called_once_with("test_user")
    
    def test_get_existing_scheduler(self):
        """Test getting existing scheduler"""
        with patch('utils.scheduler.DailyScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler
            
            manager = SchedulerManager()
            
            # First call creates scheduler
            scheduler1 = manager.get_scheduler("test_user")
            # Second call returns same scheduler
            scheduler2 = manager.get_scheduler("test_user")
            
            assert scheduler1 == scheduler2
            assert mock_scheduler_class.call_count == 1
    
    @pytest.mark.asyncio
    async def test_start_all_schedulers(self):
        """Test starting all schedulers"""
        mock_scheduler1 = Mock()
        mock_scheduler1.start_scheduler = AsyncMock()
        mock_scheduler2 = Mock()
        mock_scheduler2.start_scheduler = AsyncMock()
        
        manager = SchedulerManager()
        manager.schedulers = {
            "user1": mock_scheduler1,
            "user2": mock_scheduler2
        }
        
        # Mock asyncio.gather to avoid actually waiting
        with patch('asyncio.gather') as mock_gather:
            mock_gather.return_value = asyncio.Future()
            mock_gather.return_value.set_result(None)
            
            with patch('asyncio.create_task') as mock_create_task:
                mock_task1 = Mock()
                mock_task2 = Mock()
                mock_create_task.side_effect = [mock_task1, mock_task2]
                
                await manager.start_all_schedulers()
                
                assert mock_create_task.call_count == 2
                mock_gather.assert_called_once_with(mock_task1, mock_task2)
    
    def test_stop_all_schedulers(self):
        """Test stopping all schedulers"""
        mock_scheduler1 = Mock()
        mock_scheduler2 = Mock()
        
        manager = SchedulerManager()
        manager.schedulers = {
            "user1": mock_scheduler1,
            "user2": mock_scheduler2
        }
        
        manager.stop_all_schedulers()
        
        mock_scheduler1.stop_scheduler.assert_called_once()
        mock_scheduler2.stop_scheduler.assert_called_once()


@pytest.mark.unit
class TestSchedulerUtilities:
    """Test scheduler utility functions"""
    
    def test_create_scheduler_for_user(self):
        """Test utility function for creating scheduler"""
        with patch('utils.scheduler.DailyScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler
            
            from utils.scheduler import create_scheduler_for_user
            
            scheduler = create_scheduler_for_user("test_user")
            
            assert scheduler == mock_scheduler
            mock_scheduler_class.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_run_scheduler_with_workflow(self):
        """Test utility function for running scheduler with workflow"""
        mock_scheduler = Mock()
        mock_scheduler.set_workflow_nodes = Mock()
        mock_scheduler.start_scheduler = AsyncMock()
        mock_scheduler.stop_scheduler = Mock()
        
        workflow_nodes = {"test_node": Mock()}
        
        with patch('utils.scheduler.DailyScheduler', return_value=mock_scheduler):
            from utils.scheduler import run_scheduler_with_workflow
            
            try:
                await run_scheduler_with_workflow("test_user", workflow_nodes)
            except asyncio.CancelledError:
                pass  # Expected when task is cancelled
            
            mock_scheduler.set_workflow_nodes.assert_called_once_with(workflow_nodes)
            mock_scheduler.start_scheduler.assert_called_once()