"""
Unit tests for Google Calendar integration
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from freezegun import freeze_time

from utils.google_calendar import GoogleCalendarManager


class TestGoogleCalendarManager:
    """Test Google Calendar Manager"""
    
    @patch('utils.google_calendar.os.path.exists')
    def test_calendar_manager_no_credentials(self, mock_exists):
        """Test calendar manager when no credentials exist"""
        mock_exists.return_value = False
        
        manager = GoogleCalendarManager("test_user")
        
        assert not manager.is_available()
        assert manager.service is None
        assert manager.credentials is None
    
    def test_calendar_manager_format_events(self, mock_calendar_events):
        """Test formatting events for display"""
        manager = GoogleCalendarManager("test_user")
        formatted = manager.format_events_for_display(mock_calendar_events)
        
        assert "09:00 - 10:00: Morning Meeting" in formatted
        assert "Conference Room A" in formatted
        assert "All day: All Day Event" in formatted
        assert "Convention Center" in formatted
    
    def test_format_empty_events(self):
        """Test formatting empty events list"""
        manager = GoogleCalendarManager("test_user")
        formatted = manager.format_events_for_display([])
        
        assert formatted == "No events found."
    
    @freeze_time("2024-01-15 10:00:00")
    def test_process_event_timed(self):
        """Test processing a timed calendar event"""
        manager = GoogleCalendarManager("test_user")
        
        raw_event = {
            'id': 'test_event',
            'summary': 'Test Meeting',
            'description': 'A test meeting',
            'start': {'dateTime': '2024-01-15T14:00:00Z'},
            'end': {'dateTime': '2024-01-15T15:00:00Z'},
            'location': 'Room 123',
            'status': 'confirmed',
            'htmlLink': 'https://calendar.google.com/event'
        }
        
        processed = manager._process_event(raw_event)
        
        assert processed['summary'] == 'Test Meeting'
        assert processed['is_all_day'] is False
        assert processed['duration_minutes'] == 60
        assert processed['location'] == 'Room 123'
    
    @freeze_time("2024-01-15 10:00:00")
    def test_process_event_all_day(self):
        """Test processing an all-day calendar event"""
        manager = GoogleCalendarManager("test_user")
        
        raw_event = {
            'id': 'test_event',
            'summary': 'All Day Event',
            'start': {'date': '2024-01-15'},
            'end': {'date': '2024-01-16'},
            'status': 'confirmed'
        }
        
        processed = manager._process_event(raw_event)
        
        assert processed['summary'] == 'All Day Event'
        assert processed['is_all_day'] is True
        assert processed['duration_minutes'] is None
    
    def test_process_invalid_event(self):
        """Test processing an invalid event"""
        manager = GoogleCalendarManager("test_user")
        
        invalid_event = {
            'id': 'invalid',
            'summary': 'Invalid Event'
            # Missing start/end times
        }
        
        processed = manager._process_event(invalid_event)
        assert processed is None
    
    @patch.object(GoogleCalendarManager, 'get_todays_events')
    @patch.object(GoogleCalendarManager, 'get_next_event')
    def test_get_calendar_context_for_planning(self, mock_next_event, mock_today_events, mock_calendar_events):
        """Test getting calendar context for planning"""
        manager = GoogleCalendarManager("test_user")
        manager.service = Mock()  # Mock that service is available
        
        mock_today_events.return_value = mock_calendar_events
        mock_next_event.return_value = mock_calendar_events[0]
        
        context = manager.get_calendar_context_for_planning()
        
        assert context['has_calendar_access'] is True
        assert context['today_events_count'] == 3
        assert context['today_events'] == mock_calendar_events
        assert context['next_event'] == mock_calendar_events[0]
        assert 'calendar_summary' in context


@pytest.mark.calendar
class TestGoogleCalendarIntegration:
    """Integration tests for Google Calendar (require actual credentials)"""
    
    @pytest.mark.slow
    def test_real_calendar_connection(self):
        """Test actual calendar connection (requires setup)"""
        # This test should be skipped in CI/automated testing
        # Only run when testing with real credentials
        manager = GoogleCalendarManager("alex")
        
        if manager.is_available():
            # Test basic functionality
            events = manager.get_todays_events()
            assert isinstance(events, list)
            
            next_event = manager.get_next_event()
            # next_event can be None if no upcoming events
            if next_event:
                assert 'summary' in next_event
                assert 'start_time' in next_event
        else:
            pytest.skip("Google Calendar not configured for testing")


class TestCalendarUtilityFunctions:
    """Test utility functions"""
    
    def test_create_test_calendar_event(self):
        """Test utility function for creating test events"""
        from tests.conftest import create_test_calendar_event
        
        event = create_test_calendar_event("Test Meeting", 14, 90)
        
        assert event['summary'] == "Test Meeting"
        assert event['start_time'].hour == 14
        assert event['duration_minutes'] == 90
        assert event['is_all_day'] is False
    
    def test_create_all_day_test_event(self):
        """Test creating all-day test event"""
        from tests.conftest import create_test_calendar_event
        
        event = create_test_calendar_event("Conference", 0, is_all_day=True)
        
        assert event['summary'] == "Conference"
        assert event['is_all_day'] is True
        assert event['duration_minutes'] is None


@pytest.mark.unit
class TestCalendarErrorHandling:
    """Test error handling in calendar functionality"""
    
    @patch('utils.google_calendar.Credentials.from_authorized_user_file')
    def test_invalid_token_handling(self, mock_credentials):
        """Test handling of invalid token file"""
        mock_credentials.side_effect = ValueError("Invalid token format")
        
        with patch('utils.google_calendar.os.path.exists', return_value=True):
            with patch('utils.google_calendar.os.remove') as mock_remove:
                manager = GoogleCalendarManager("test_user")
                
                # Should have removed the invalid token file
                mock_remove.assert_called()
                assert not manager.is_available()
    
    @patch.object(GoogleCalendarManager, '_setup_credentials')
    def test_calendar_methods_without_service(self, mock_setup):
        """Test calendar methods when service is not available"""
        mock_setup.return_value = None
        manager = GoogleCalendarManager("test_user")
        manager.service = None
        
        # All methods should handle missing service gracefully
        assert manager.get_todays_events() == []
        assert manager.get_upcoming_events() == []
        assert manager.get_next_event() is None
        assert not manager.is_available()
    
    @patch.object(GoogleCalendarManager, 'get_todays_events')
    def test_calendar_context_without_access(self, mock_today_events):
        """Test calendar context when no access is available"""
        manager = GoogleCalendarManager("test_user")
        manager.service = None
        mock_today_events.return_value = []
        
        context = manager.get_calendar_context_for_planning()
        
        assert context['has_calendar_access'] is False
        assert context['today_events_count'] == 0
        assert context['calendar_summary'] == "No events today"