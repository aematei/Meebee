"""
Integration tests for Telegram bot functionality
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from utils.telegram_bot import TelegramBotInterface


@pytest.mark.telegram
class TestTelegramBotInterface:
    """Test Telegram bot interface"""
    
    @patch('utils.telegram_bot.Bot')
    def test_telegram_bot_initialization(self, mock_bot):
        """Test Telegram bot initialization"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            assert bot_interface.token == 'test_token'
            assert bot_interface.chat_id == 'test_chat_id'
            assert bot_interface.message_handler is None
            assert bot_interface.command_handlers == {}
    
    def test_telegram_bot_missing_env_vars(self):
        """Test Telegram bot initialization with missing environment variables"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                TelegramBotInterface()
            
            assert "TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set" in str(exc_info.value)
    
    @patch('utils.telegram_bot.Bot')
    def test_set_message_handler(self, mock_bot):
        """Test setting message handler"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            async def test_handler(message, user_id):
                return f"Response to {message} from {user_id}"
            
            bot_interface.set_message_handler(test_handler)
            assert bot_interface.message_handler == test_handler
    
    @patch('utils.telegram_bot.Bot')
    def test_add_command_handler(self, mock_bot):
        """Test adding command handlers"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            async def test_command_handler(update, context):
                await update.message.reply_text("Test response")
            
            bot_interface.add_command_handler("test", test_command_handler)
            assert "test" in bot_interface.command_handlers
            assert bot_interface.command_handlers["test"] == test_command_handler
    
    @patch('utils.telegram_bot.Bot')
    async def test_start_command(self, mock_bot, mock_telegram_update):
        """Test /start command handler"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            await bot_interface.start_command(mock_telegram_update, None)
            
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "personal AI assistant" in call_args.lower()
    
    @patch('utils.telegram_bot.Bot')
    async def test_help_command(self, mock_bot, mock_telegram_update):
        """Test /help command handler"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            await bot_interface.help_command(mock_telegram_update, None)
            
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "/start" in call_args
            assert "/help" in call_args
            assert "/calendar" in call_args
    
    @patch('utils.telegram_bot.Bot')
    async def test_handle_message_with_handler(self, mock_bot, mock_telegram_update):
        """Test message handling with a message handler"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            # Set up message handler
            async def mock_handler(message, user_id):
                return f"Handled: {message} from {user_id}"
            
            bot_interface.set_message_handler(mock_handler)
            
            # Test message handling
            await bot_interface.handle_message(mock_telegram_update, None)
            
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "Handled: Test message from 123456789" == call_args
    
    @patch('utils.telegram_bot.Bot')
    async def test_handle_message_without_handler(self, mock_bot, mock_telegram_update):
        """Test message handling without a message handler"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            
            await bot_interface.handle_message(mock_telegram_update, None)
            
            mock_telegram_update.message.reply_text.assert_called_once()
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "still setting up" in call_args.lower()
    
    @patch('utils.telegram_bot.Bot')
    async def test_send_message(self, mock_bot):
        """Test sending a message"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            bot_interface.bot.send_message = AsyncMock()
            
            result = await bot_interface.send_message("Test message")
            
            assert result is True
            bot_interface.bot.send_message.assert_called_once_with(
                chat_id='test_chat_id',
                text="Test message"
            )
    
    @patch('utils.telegram_bot.Bot')
    async def test_send_message_custom_chat(self, mock_bot):
        """Test sending a message to custom chat ID"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            bot_interface.bot.send_message = AsyncMock()
            
            result = await bot_interface.send_message("Test message", "custom_chat_id")
            
            assert result is True
            bot_interface.bot.send_message.assert_called_once_with(
                chat_id='custom_chat_id',
                text="Test message"
            )
    
    @patch('utils.telegram_bot.Bot')
    async def test_send_message_error_handling(self, mock_bot):
        """Test error handling in send_message"""
        with patch.dict('os.environ', {
            'TELEGRAM_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'test_chat_id'
        }):
            bot_interface = TelegramBotInterface()
            bot_interface.bot.send_message = AsyncMock(side_effect=Exception("Network error"))
            
            result = await bot_interface.send_message("Test message")
            
            assert result is False


@pytest.mark.telegram
class TestTelegramIntegrationWithMain:
    """Test Telegram integration with main application"""
    
    @patch('main.TelegramBotInterface')
    @patch('main.create_google_calendar_manager')
    def test_personal_assistant_telegram_setup(self, mock_calendar_manager, mock_telegram_interface):
        """Test PersonalAssistant Telegram setup"""
        from main import PersonalAssistant
        
        mock_bot = Mock()
        mock_telegram_interface.return_value = mock_bot
        mock_calendar_manager.return_value = Mock()
        
        assistant = PersonalAssistant()
        
        # Verify Telegram bot was initialized
        mock_telegram_interface.assert_called_once()
        
        # Verify message handler was set
        mock_bot.set_message_handler.assert_called_once()
        
        # Verify command handlers were added
        expected_commands = ["status", "plan", "calendar", "today", "next", "calendar_setup"]
        assert mock_bot.add_command_handler.call_count == len(expected_commands)
        
        # Check that all expected commands were registered
        registered_commands = [call[0][0] for call in mock_bot.add_command_handler.call_args_list]
        for command in expected_commands:
            assert command in registered_commands
    
    @patch('main.TelegramBotInterface')
    @patch('main.create_google_calendar_manager')
    @patch('main.handle_interrupt')
    @patch('main.should_interrupt')
    async def test_handle_telegram_message_interrupt(self, mock_should_interrupt, mock_handle_interrupt,
                                                   mock_calendar_manager, mock_telegram_interface):
        """Test handling Telegram message as interrupt"""
        from main import PersonalAssistant
        
        mock_bot = Mock()
        mock_telegram_interface.return_value = mock_bot
        mock_calendar_manager.return_value = Mock()
        
        assistant = PersonalAssistant()
        assistant.current_state = {
            "messages": [],
            "user_context": {"user_id": "test_user"},
            "current_phase": "morning_checkin"
        }
        
        # Configure mocks
        mock_should_interrupt.return_value = True
        mock_handle_interrupt.return_value = {
            "messages": [
                {"role": "user", "content": "Help message"},
                {"role": "assistant", "content": "I'm here to help!"}
            ]
        }
        
        result = await assistant.handle_telegram_message("I need help!", "test_user")
        
        assert result == "I'm here to help!"
        mock_should_interrupt.assert_called_once()
        mock_handle_interrupt.assert_called_once()
    
    @patch('main.TelegramBotInterface')
    @patch('main.create_google_calendar_manager')
    async def test_get_calendar_message(self, mock_calendar_manager, mock_telegram_interface):
        """Test getting calendar message"""
        from main import PersonalAssistant
        
        mock_bot = Mock()
        mock_telegram_interface.return_value = mock_bot
        
        # Setup calendar manager mock
        mock_manager = Mock()
        mock_manager.is_available.return_value = True
        mock_manager.get_todays_events.return_value = [
            {
                'summary': 'Test Meeting',
                'start_time': Mock(),
                'is_all_day': False
            }
        ]
        mock_manager.get_upcoming_events.return_value = []
        mock_manager.format_events_for_display.return_value = "• 09:00 - 10:00: Test Meeting"
        mock_calendar_manager.return_value = mock_manager
        
        assistant = PersonalAssistant()
        
        result = await assistant.get_calendar_message()
        
        assert "Calendar Overview" in result
        assert "Test Meeting" in result
    
    @patch('main.TelegramBotInterface')
    @patch('main.create_google_calendar_manager')
    async def test_get_calendar_message_not_available(self, mock_calendar_manager, mock_telegram_interface):
        """Test getting calendar message when calendar not available"""
        from main import PersonalAssistant
        
        mock_bot = Mock()
        mock_telegram_interface.return_value = mock_bot
        
        # Setup calendar manager mock
        mock_manager = Mock()
        mock_manager.is_available.return_value = False
        mock_calendar_manager.return_value = mock_manager
        
        assistant = PersonalAssistant()
        
        result = await assistant.get_calendar_message()
        
        assert "Google Calendar is not set up yet" in result
        assert "/calendar_setup" in result


@pytest.mark.telegram
class TestTelegramUtilityFunctions:
    """Test Telegram utility functions"""
    
    @patch('utils.telegram_bot.TelegramBotInterface')
    async def test_send_telegram_message_utility(self, mock_telegram_interface):
        """Test utility function for sending messages"""
        from utils.telegram_bot import send_telegram_message
        
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock(return_value=True)
        mock_telegram_interface.return_value = mock_bot
        
        result = await send_telegram_message("Test message", "test_chat_id")
        
        assert result is True
        mock_bot.send_message.assert_called_once_with("Test message", "test_chat_id")
    
    @patch('utils.telegram_bot.TelegramBotInterface')
    def test_create_bot_interface_factory(self, mock_telegram_interface):
        """Test factory function for creating bot interface"""
        from utils.telegram_bot import create_bot_interface
        
        mock_bot = Mock()
        mock_telegram_interface.return_value = mock_bot
        
        result = create_bot_interface()
        
        assert result == mock_bot
        mock_telegram_interface.assert_called_once()