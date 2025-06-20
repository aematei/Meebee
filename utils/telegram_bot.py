import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TelegramBotInterface:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = Bot(token=self.token)
        self.application = None
        self.message_handler: Optional[Callable] = None
        self.command_handlers: Dict[str, Callable] = {}
        
        if not self.token or not self.chat_id:
            raise ValueError("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set in environment variables")
    
    def set_message_handler(self, handler: Callable[[str, str], str]):
        """Set the handler function for incoming messages"""
        self.message_handler = handler
    
    def add_command_handler(self, command: str, handler: Callable):
        """Add a command handler"""
        self.command_handlers[command] = handler
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "Hello! I'm your personal AI assistant. I'm here to provide gentle awareness "
            "nudging throughout the day to help with time awareness and executive function. "
            "Let's start with a quick check-in!"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
Available commands:
/start - Start the assistant
/help - Show this help message
/status - Check current status
/plan - View current daily plan

Calendar commands:
/calendar - Calendar overview (today + tomorrow)
/today - Today's events
/next - Next upcoming event
/calendar_setup - Instructions for Google Calendar setup

Just send me a message and I'll respond based on our current phase of the day!
        """
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        if not update.message or not update.message.text:
            return
        
        user_message = update.message.text
        user_id = str(update.effective_user.id)
        
        logger.info(f"Received message from {user_id}: {user_message}")
        
        try:
            if self.message_handler:
                response = await self.message_handler(user_message, user_id)
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("I'm still setting up. Please try again in a moment!")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("Sorry, I encountered an error. Please try again.")
    
    async def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Send a message to the specified chat (or default chat)"""
        target_chat_id = chat_id or self.chat_id
        try:
            await self.bot.send_message(chat_id=target_chat_id, text=message)
            logger.info(f"Message sent to {target_chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def setup_application(self):
        """Setup the Telegram application with handlers"""
        self.application = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Add custom command handlers
        for command, handler in self.command_handlers.items():
            self.application.add_handler(CommandHandler(command, handler))
        
        # Add message handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        logger.info("Telegram application setup complete")
    
    def start_polling(self):
        """Start polling for messages (synchronous)"""
        if not self.application:
            self.setup_application()
        
        logger.info("Starting Telegram bot polling...")
        
        # Use the synchronous run_polling method
        self.application.run_polling(drop_pending_updates=True)
    
    async def stop(self):
        """Stop the bot"""
        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")


# Utility functions for easy integration
async def send_telegram_message(message: str, chat_id: Optional[str] = None) -> bool:
    """Utility function to send a single message"""
    bot_interface = TelegramBotInterface()
    return await bot_interface.send_message(message, chat_id)


def create_bot_interface() -> TelegramBotInterface:
    """Factory function to create a bot interface"""
    return TelegramBotInterface()