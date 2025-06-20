import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from models.agent_state import AgentState, create_initial_state
from models.user import User
from nodes.planning import morning_planning, nighttime_planning
from nodes.checkins import morning_checkin, midday_checkin, evening_checkin
from nodes.interrupts import handle_interrupt, should_interrupt
from utils.telegram_bot import TelegramBotInterface
from utils.google_calendar import create_google_calendar_manager, setup_google_calendar_instructions
from utils.scheduler import DailyScheduler
from dotenv import load_dotenv
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load environment and configure timezone for deployment
load_dotenv()

# Import timezone helper to configure timezone on startup
from utils.timezone_helper import set_timezone_for_deployment
set_timezone_for_deployment()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for deployment platforms"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "personal-assistant"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging to avoid spam
        pass


class PersonalAssistant:
    def __init__(self):
        self.telegram_bot = TelegramBotInterface()
        self.workflow = None
        self.memory = MemorySaver()
        self.current_state = None
        self.scheduler = None
        self.scheduler_task = None
        self.setup_workflow()
        self.setup_telegram_bot()
        self.setup_scheduler()
    
    def setup_workflow(self):
        """Setup the LangGraph workflow"""
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("morning_planning", morning_planning)
        workflow.add_node("morning_checkin", morning_checkin)
        workflow.add_node("midday_checkin", midday_checkin)
        workflow.add_node("evening_checkin", evening_checkin)
        workflow.add_node("nighttime_planning", nighttime_planning)
        
        # Add edges (the daily cycle)
        workflow.add_edge("morning_planning", "morning_checkin")
        workflow.add_edge("morning_checkin", "midday_checkin")
        workflow.add_edge("midday_checkin", "evening_checkin")
        workflow.add_edge("evening_checkin", "nighttime_planning")
        workflow.add_edge("nighttime_planning", "morning_planning")  # Cycle back
        
        # Set the entry point
        workflow.set_entry_point("morning_planning")
        
        # Compile the workflow
        self.workflow = workflow.compile(checkpointer=self.memory)
        
        logger.info("LangGraph workflow setup complete")
    
    def setup_scheduler(self):
        """Setup the daily scheduler"""
        self.scheduler = DailyScheduler("alex", self.telegram_bot)
        
        # Set up workflow nodes for the scheduler
        workflow_nodes = {
            "morning_planning": morning_planning,
            "morning_checkin": morning_checkin,
            "midday_checkin": midday_checkin,
            "evening_checkin": evening_checkin,
            "nighttime_planning": nighttime_planning
        }
        self.scheduler.set_workflow_nodes(workflow_nodes)
        
        logger.info("Daily scheduler setup complete")
    
    def setup_telegram_bot(self):
        """Setup Telegram bot handlers"""
        # Set the message handler
        self.telegram_bot.set_message_handler(self.handle_telegram_message)
        
        # Add custom command handlers
        async def status_command(update, context):
            status_msg = await self.get_status_message()
            await update.message.reply_text(status_msg)
        
        async def plan_command(update, context):
            plan_msg = await self.get_plan_message()
            await update.message.reply_text(plan_msg)
        
        async def calendar_command(update, context):
            calendar_msg = await self.get_calendar_message()
            await update.message.reply_text(calendar_msg)
        
        async def today_command(update, context):
            today_msg = await self.get_today_events_message()
            await update.message.reply_text(today_msg)
        
        async def next_command(update, context):
            next_msg = await self.get_next_event_message()
            await update.message.reply_text(next_msg)
        
        async def calendar_setup_command(update, context):
            setup_msg = setup_google_calendar_instructions()
            await update.message.reply_text(setup_msg)
        
        async def schedule_command(update, context):
            schedule_msg = await self.get_schedule_status_message()
            await update.message.reply_text(schedule_msg)
        
        async def scheduler_start_command(update, context):
            if self.scheduler_task and not self.scheduler_task.done():
                await update.message.reply_text("🤖 Scheduler is already running!")
            else:
                await self.start_scheduler_background()
                await update.message.reply_text("🤖 Scheduler started! I'll gently nudge you at your scheduled times.")
        
        async def scheduler_stop_command(update, context):
            if self.scheduler_task and not self.scheduler_task.done():
                self.scheduler.stop_scheduler()
                self.scheduler_task.cancel()
                await update.message.reply_text("🤖 Scheduler stopped. I won't send automatic nudges until you restart it.")
            else:
                await update.message.reply_text("🤖 Scheduler is not currently running.")
        
        self.telegram_bot.add_command_handler("status", status_command)
        self.telegram_bot.add_command_handler("plan", plan_command)
        self.telegram_bot.add_command_handler("calendar", calendar_command)
        self.telegram_bot.add_command_handler("today", today_command)
        self.telegram_bot.add_command_handler("next", next_command)
        self.telegram_bot.add_command_handler("calendar_setup", calendar_setup_command)
        self.telegram_bot.add_command_handler("schedule", schedule_command)
        self.telegram_bot.add_command_handler("start_scheduler", scheduler_start_command)
        self.telegram_bot.add_command_handler("stop_scheduler", scheduler_stop_command)
        
        logger.info("Telegram bot handlers setup complete")
    
    async def handle_telegram_message(self, message: str, user_id: str) -> str:
        """Handle incoming Telegram messages"""
        logger.info(f"Processing message from {user_id}: {message}")
        
        try:
            # Initialize state if needed
            if self.current_state is None:
                self.current_state = create_initial_state(user_id)
            
            # Check if this should be handled as an interrupt
            if should_interrupt(self.current_state, message):
                # Handle as interrupt
                self.current_state = await handle_interrupt(self.current_state, message)
                
                # Get the last assistant message to return
                last_message = None
                for msg in reversed(self.current_state["messages"]):
                    if msg["role"] == "assistant":
                        last_message = msg["content"]
                        break
                
                return last_message or "I'm here to help! How can I support you right now?"
            
            else:
                # Process through normal workflow
                config = {"configurable": {"thread_id": f"user_{user_id}"}}
                
                # Add user message to state
                self.current_state["messages"].append({
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat(),
                    "phase": self.current_state["current_phase"]
                })
                
                # Run the workflow
                result = await self.workflow.ainvoke(self.current_state, config)
                self.current_state = result
                
                # Get the last assistant message
                last_message = None
                for msg in reversed(result["messages"]):
                    if msg["role"] == "assistant":
                        last_message = msg["content"]
                        break
                
                return last_message or "I'm processing your request. Please give me a moment!"
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return "I'm sorry, I encountered an error. Please try again in a moment."
    
    async def get_status_message(self) -> str:
        """Get current status message"""
        if self.current_state is None:
            return "I'm ready to start! Send me a message to begin our daily journey together."
        
        current_phase = self.current_state.get("current_phase", "unknown")
        last_activity = self.current_state.get("last_activity")
        
        status = f"Current phase: {current_phase.replace('_', ' ').title()}"
        
        if last_activity:
            status += f"\nLast activity: {last_activity}"
        
        if self.current_state.get("daily_plan"):
            status += f"\n\nToday's plan: {self.current_state['daily_plan']['content'][:100]}..."
        
        return status
    
    async def get_plan_message(self) -> str:
        """Get current plan message"""
        if self.current_state is None or not self.current_state.get("daily_plan"):
            return "No plan has been created yet. Let's start with a morning planning session!"
        
        plan = self.current_state["daily_plan"]
        return f"Today's plan:\n\n{plan['content']}\n\nCreated: {plan['metadata']['created']}\nLast updated: {plan['metadata']['last_updated']}"
    
    async def get_calendar_message(self) -> str:
        """Get calendar overview message"""
        calendar_manager = create_google_calendar_manager("alex")
        
        if not calendar_manager.is_available():
            return "📅 Google Calendar is not set up yet. Use /calendar_setup for instructions."
        
        today_events = calendar_manager.get_todays_events()
        upcoming_events = calendar_manager.get_upcoming_events(hours=48)
        
        message = "📅 **Calendar Overview**\n\n"
        
        if today_events:
            message += f"**Today ({len(today_events)} events):**\n"
            message += calendar_manager.format_events_for_display(today_events)
        else:
            message += "**Today:** No events scheduled"
        
        tomorrow_events = [e for e in upcoming_events if e['start_time'].date() > datetime.now().date()]
        if tomorrow_events:
            message += f"\n\n**Tomorrow ({len(tomorrow_events)} events):**\n"
            message += calendar_manager.format_events_for_display(tomorrow_events[:5])
        
        return message
    
    async def get_today_events_message(self) -> str:
        """Get today's events message"""
        calendar_manager = create_google_calendar_manager("alex")
        
        if not calendar_manager.is_available():
            return "📅 Google Calendar is not set up yet. Use /calendar_setup for instructions."
        
        today_events = calendar_manager.get_todays_events()
        
        if not today_events:
            return "📅 No events scheduled for today. You have a clear calendar!"
        
        message = f"📅 **Today's Schedule ({len(today_events)} events):**\n\n"
        message += calendar_manager.format_events_for_display(today_events)
        
        return message
    
    async def get_next_event_message(self) -> str:
        """Get next event message"""
        calendar_manager = create_google_calendar_manager("alex")
        
        if not calendar_manager.is_available():
            return "📅 Google Calendar is not set up yet. Use /calendar_setup for instructions."
        
        next_event = calendar_manager.get_next_event()
        
        if not next_event:
            return "📅 No upcoming events in the next 24 hours."
        
        if next_event['is_all_day']:
            time_str = "All day"
        else:
            time_str = next_event['start_time'].strftime("%H:%M")
            if next_event['start_time'].date() != datetime.now().date():
                time_str = next_event['start_time'].strftime("%a %H:%M")
        
        message = f"📅 **Next Event:**\n\n"
        message += f"• {time_str}: {next_event['summary']}"
        
        if next_event['location']:
            message += f"\n📍 {next_event['location']}"
        
        if next_event['description']:
            message += f"\n📝 {next_event['description'][:100]}..."
        
        return message
    
    async def get_schedule_status_message(self) -> str:
        """Get schedule status message"""
        if not self.scheduler:
            return "🤖 Scheduler is not initialized."
        
        status = self.scheduler.get_schedule_status()
        
        from utils.timezone_helper import format_time_for_user
        message = "🕐 **Schedule Status**\n\n"
        message += f"📅 Current time: {format_time_for_user()}\n"
        message += f"🎯 Current phase: {status['current_phase'].replace('_', ' ').title()}\n"
        message += f"⏰ Expected phase: {status['expected_phase'].replace('_', ' ').title()}\n"
        
        if status['is_on_schedule']:
            message += "✅ On schedule\n"
        else:
            message += "⚠️ Behind schedule\n"
        
        message += "\n**Daily Schedule:**\n"
        for phase, time_str in status['schedule'].items():
            emoji = "✅" if phase == status['current_phase'] else "⏰"
            message += f"{emoji} {phase.replace('_', ' ').title()}: {time_str}\n"
        
        if status['next_phase_info']:
            next_info = status['next_phase_info']
            message += f"\n**Next:** {next_info['phase'].replace('_', ' ').title()} in {next_info['minutes_until']} minutes"
        
        if self.scheduler_task and not self.scheduler_task.done():
            message += "\n\n🤖 **Scheduler Status:** Running (automatic nudges enabled)"
        else:
            message += "\n\n🤖 **Scheduler Status:** Stopped (use /start_scheduler to enable)"
        
        return message
    
    async def start_scheduler_background(self):
        """Start the scheduler in the background"""
        if self.scheduler_task and not self.scheduler_task.done():
            return  # Already running
        
        self.scheduler_task = asyncio.create_task(self.scheduler.start_scheduler())
        logger.info("Started scheduler background task")
    
    async def run_daily_cycle_demo(self):
        """Run a demo of the daily cycle for testing"""
        logger.info("Starting daily cycle demo")
        
        # Initialize state
        state = create_initial_state("alex")
        config = {"configurable": {"thread_id": "demo_thread"}}
        
        # Simulate going through each phase
        phases = ["morning_planning", "morning_checkin", "midday_checkin", "evening_checkin", "nighttime_planning"]
        
        for phase in phases:
            logger.info(f"Demo: Executing {phase}")
            
            # Update current phase
            state["current_phase"] = phase
            
            # Run the workflow
            result = await self.workflow.ainvoke(state, config)
            state = result
            
            # Get the last message
            if result["messages"]:
                last_msg = result["messages"][-1]
                print(f"\n--- {phase.upper().replace('_', ' ')} ---")
                print(f"Assistant: {last_msg['content']}")
                print("-" * 50)
            
            # Small delay between phases
            await asyncio.sleep(1)
        
        logger.info("Daily cycle demo completed")
    
    def start_health_server(self):
        """Start health check server in background thread"""
        port = int(os.getenv('PORT', 8080))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Starting health check server on port {port}")
        
        def run_server():
            server.serve_forever()
        
        health_thread = threading.Thread(target=run_server, daemon=True)
        health_thread.start()
        return server
    
    def start(self):
        """Start the personal assistant"""
        logger.info("Starting Personal Assistant")
        
        try:
            # Start health check server for deployment platforms
            health_server = self.start_health_server()
            
            # Initialize user data
            user = User.load_or_create("alex")
            user.save()
            
            # Skip the startup message for now to avoid event loop issues
            logger.info("Skipping startup message - will send when first user interacts")
            
            # Start Telegram polling (this blocks)
            self.telegram_bot.start_polling()
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            # Stop scheduler if running
            if self.scheduler:
                self.scheduler.stop_scheduler()
            if self.scheduler_task and not self.scheduler_task.done():
                self.scheduler_task.cancel()
        except Exception as e:
            logger.error(f"Error starting assistant: {e}")


def main():
    """Main entry point"""
    assistant = PersonalAssistant()
    
    # For testing, you can run the demo cycle
    # asyncio.run(assistant.run_daily_cycle_demo())
    
    # Start the main assistant
    assistant.start()


if __name__ == "__main__":
    main()