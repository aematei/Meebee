"""
Scheduler module for automatic daily cycle progression and time-based check-ins
"""
import asyncio
import json
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from models.agent_state import create_initial_state
from models.user import User
from utils.telegram_bot import TelegramBotInterface


class SchedulerState:
    """Manages scheduler state persistence"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state_file = Path(f"data/users/{user_id}/scheduler_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load scheduler state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return {
            "last_phase_transition": None,
            "current_phase": "morning_planning",
            "daily_cycle_count": 0,
            "last_check_in_times": {},
            "missed_check_ins": [],
            "nudge_history": []
        }
    
    def _save_state(self):
        """Save scheduler state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2, default=str)
    
    def get(self, key: str, default=None):
        """Get state value"""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set state value and save"""
        self._state[key] = value
        self._save_state()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple state values"""
        self._state.update(updates)
        self._save_state()


class DailyScheduler:
    """
    Handles automatic daily cycle progression and time-based check-ins
    """
    
    # Default schedule times (can be customized per user)
    DEFAULT_SCHEDULE = {
        "morning_planning": time(7, 0),     # 7:00 AM
        "morning_checkin": time(9, 0),      # 9:00 AM
        "midday_checkin": time(13, 0),      # 1:00 PM
        "evening_checkin": time(18, 0),     # 6:00 PM
        "nighttime_planning": time(21, 0)   # 9:00 PM
    }
    
    # Grace periods for check-ins (minutes)
    GRACE_PERIODS = {
        "morning_planning": 120,    # 2 hours
        "morning_checkin": 180,     # 3 hours
        "midday_checkin": 240,      # 4 hours
        "evening_checkin": 180,     # 3 hours
        "nighttime_planning": 120   # 2 hours
    }
    
    def __init__(self, user_id: str = "alex", telegram_bot: Optional[TelegramBotInterface] = None):
        self.user_id = user_id
        self.state = SchedulerState(user_id)
        self.telegram_bot = telegram_bot or TelegramBotInterface()
        self.logger = logging.getLogger(f"scheduler.{user_id}")
        
        # Load user's custom schedule if available
        self.schedule = self._load_user_schedule()
        
        # Workflow node functions (will be set when integrating with main app)
        self.workflow_nodes: Dict[str, Callable] = {}
        
        # Running flag
        self.is_running = False
        
    def _load_user_schedule(self) -> Dict[str, time]:
        """Load user's custom schedule or use defaults"""
        user_schedule_file = Path(f"data/users/{self.user_id}/schedule.json")
        
        if user_schedule_file.exists():
            try:
                with open(user_schedule_file, 'r') as f:
                    schedule_data = json.load(f)
                
                # Convert time strings back to time objects
                schedule = {}
                for phase, time_str in schedule_data.items():
                    hour, minute = map(int, time_str.split(':'))
                    schedule[phase] = time(hour, minute)
                
                self.logger.info(f"Loaded custom schedule for {self.user_id}")
                return schedule
            except (json.JSONDecodeError, ValueError, FileNotFoundError):
                self.logger.warning(f"Error loading custom schedule, using defaults")
        
        return self.DEFAULT_SCHEDULE.copy()
    
    def set_workflow_nodes(self, nodes: Dict[str, Callable]):
        """Set the workflow node functions"""
        self.workflow_nodes = nodes
    
    def update_schedule(self, phase: str, new_time: time):
        """Update schedule for a specific phase"""
        if phase not in self.DEFAULT_SCHEDULE:
            raise ValueError(f"Invalid phase: {phase}")
        
        self.schedule[phase] = new_time
        self._save_user_schedule()
        self.logger.info(f"Updated {phase} schedule to {new_time}")
    
    def _save_user_schedule(self):
        """Save user's custom schedule"""
        user_schedule_file = Path(f"data/users/{self.user_id}/schedule.json")
        user_schedule_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert time objects to strings for JSON serialization
        schedule_data = {
            phase: t.strftime("%H:%M") for phase, t in self.schedule.items()
        }
        
        with open(user_schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
    
    def get_next_phase(self, current_phase: str) -> str:
        """Get the next phase in the daily cycle"""
        phase_order = [
            "morning_planning",
            "morning_checkin", 
            "midday_checkin",
            "evening_checkin",
            "nighttime_planning"
        ]
        
        try:
            current_index = phase_order.index(current_phase)
            next_index = (current_index + 1) % len(phase_order)
            return phase_order[next_index]
        except ValueError:
            return "morning_planning"  # Default fallback
    
    def get_current_expected_phase(self) -> str:
        """Determine what phase should be active based on current time"""
        now = datetime.now().time()
        
        # Sort phases by time
        sorted_phases = sorted(self.schedule.items(), key=lambda x: x[1])
        
        # Start with the last phase as default (for early morning hours)
        current_expected = sorted_phases[-1][0]
        
        for phase, phase_time in sorted_phases:
            if now >= phase_time:
                current_expected = phase
            else:
                break
        
        return current_expected
    
    def is_check_in_overdue(self, phase: str) -> bool:
        """Check if a phase check-in is overdue"""
        if phase not in self.schedule:
            return False
        
        scheduled_time = self.schedule[phase]
        grace_period = self.GRACE_PERIODS.get(phase, 180)  # Default 3 hours
        
        now = datetime.now()
        scheduled_datetime = datetime.combine(now.date(), scheduled_time)
        
        # If scheduled time was yesterday and we're past midnight
        if scheduled_datetime > now:
            scheduled_datetime -= timedelta(days=1)
        
        overdue_time = scheduled_datetime + timedelta(minutes=grace_period)
        
        return now > overdue_time
    
    def get_time_until_next_phase(self) -> Optional[Dict[str, Any]]:
        """Get time until next scheduled phase"""
        now = datetime.now()
        current_time = now.time()
        
        # Find next scheduled phase
        upcoming_phases = []
        for phase, phase_time in self.schedule.items():
            phase_datetime = datetime.combine(now.date(), phase_time)
            
            # If the time has passed today, schedule for tomorrow
            if phase_time <= current_time:
                phase_datetime += timedelta(days=1)
            
            upcoming_phases.append((phase, phase_datetime))
        
        if not upcoming_phases:
            return None
        
        # Sort by time and get the next one
        upcoming_phases.sort(key=lambda x: x[1])
        next_phase, next_datetime = upcoming_phases[0]
        
        time_delta = next_datetime - now
        
        return {
            "phase": next_phase,
            "datetime": next_datetime,
            "time_delta": time_delta,
            "minutes_until": int(time_delta.total_seconds() / 60)
        }
    
    async def send_gentle_nudge(self, phase: str, message: str):
        """Send a gentle awareness nudge via Telegram"""
        try:
            await self.telegram_bot.send_message(message)
            
            # Log the nudge
            nudge_record = {
                "timestamp": datetime.now().isoformat(),
                "phase": phase,
                "message": message
            }
            
            nudge_history = self.state.get("nudge_history", [])
            nudge_history.append(nudge_record)
            
            # Keep only last 50 nudges
            if len(nudge_history) > 50:
                nudge_history = nudge_history[-50:]
            
            self.state.set("nudge_history", nudge_history)
            self.logger.info(f"Sent gentle nudge for {phase}")
            
        except Exception as e:
            self.logger.error(f"Failed to send nudge: {e}")
    
    async def trigger_phase_transition(self, target_phase: str):
        """Trigger a phase transition via workflow"""
        if target_phase not in self.workflow_nodes:
            self.logger.error(f"No workflow node available for phase: {target_phase}")
            return False
        
        try:
            # Load current user state
            user = User.load_or_create(self.user_id)
            agent_state = create_initial_state(self.user_id)
            agent_state["current_phase"] = target_phase
            
            # Execute the workflow node
            workflow_func = self.workflow_nodes[target_phase]
            updated_state = await workflow_func(agent_state)
            
            # Update scheduler state
            self.state.update({
                "last_phase_transition": datetime.now().isoformat(),
                "current_phase": target_phase
            })
            
            # Record check-in time
            check_in_times = self.state.get("last_check_in_times", {})
            check_in_times[target_phase] = datetime.now().isoformat()
            self.state.set("last_check_in_times", check_in_times)
            
            self.logger.info(f"Successfully transitioned to {target_phase}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to transition to {target_phase}: {e}")
            return False
    
    async def check_and_handle_transitions(self):
        """Check if any phase transitions should occur and handle them"""
        expected_phase = self.get_current_expected_phase()
        current_phase = self.state.get("current_phase", "morning_planning")
        
        # If we're behind schedule, check if we should transition
        if expected_phase != current_phase:
            # Check if current phase is overdue
            if self.is_check_in_overdue(current_phase):
                self.logger.info(f"Phase {current_phase} is overdue, transitioning to {expected_phase}")
                
                # Add to missed check-ins if we're skipping phases
                phase_order = ["morning_planning", "morning_checkin", "midday_checkin", "evening_checkin", "nighttime_planning"]
                current_idx = phase_order.index(current_phase) if current_phase in phase_order else 0
                expected_idx = phase_order.index(expected_phase) if expected_phase in phase_order else 0
                
                if expected_idx > current_idx + 1:
                    # We're skipping phases
                    missed_phases = phase_order[current_idx + 1:expected_idx]
                    missed_check_ins = self.state.get("missed_check_ins", [])
                    missed_check_ins.extend([{
                        "phase": phase,
                        "missed_date": datetime.now().date().isoformat()
                    } for phase in missed_phases])
                    self.state.set("missed_check_ins", missed_check_ins)
                
                await self.trigger_phase_transition(expected_phase)
            else:
                # Send gentle nudge for upcoming transition
                time_info = self.get_time_until_next_phase()
                if time_info and time_info["minutes_until"] <= 30:  # 30 min warning
                    nudge_message = f"💙 Gentle reminder: Your {time_info['phase'].replace('_', ' ')} is coming up in {time_info['minutes_until']} minutes. No pressure! 🌱"
                    await self.send_gentle_nudge(current_phase, nudge_message)
    
    async def start_scheduler(self):
        """Start the scheduler main loop"""
        self.is_running = True
        self.logger.info(f"Starting scheduler for {self.user_id}")
        
        while self.is_running:
            try:
                await self.check_and_handle_transitions()
                
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Shorter sleep on error
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        self.logger.info(f"Stopping scheduler for {self.user_id}")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status"""
        now = datetime.now()
        current_phase = self.state.get("current_phase", "morning_planning")
        expected_phase = self.get_current_expected_phase()
        
        return {
            "current_time": now.isoformat(),
            "current_phase": current_phase,
            "expected_phase": expected_phase,
            "is_on_schedule": current_phase == expected_phase,
            "schedule": {phase: t.strftime("%H:%M") for phase, t in self.schedule.items()},
            "next_phase_info": self.get_time_until_next_phase(),
            "last_transition": self.state.get("last_phase_transition"),
            "missed_check_ins_today": [
                record for record in self.state.get("missed_check_ins", [])
                if record.get("missed_date") == now.date().isoformat()
            ]
        }


class SchedulerManager:
    """Manages multiple user schedulers"""
    
    def __init__(self):
        self.schedulers: Dict[str, DailyScheduler] = {}
        self.logger = logging.getLogger("scheduler_manager")
    
    def get_scheduler(self, user_id: str) -> DailyScheduler:
        """Get or create scheduler for user"""
        if user_id not in self.schedulers:
            self.schedulers[user_id] = DailyScheduler(user_id)
            self.logger.info(f"Created scheduler for user: {user_id}")
        
        return self.schedulers[user_id]
    
    async def start_all_schedulers(self):
        """Start all user schedulers"""
        tasks = []
        for user_id, scheduler in self.schedulers.items():
            task = asyncio.create_task(scheduler.start_scheduler())
            tasks.append(task)
            self.logger.info(f"Started scheduler task for {user_id}")
        
        if tasks:
            await asyncio.gather(*tasks)
    
    def stop_all_schedulers(self):
        """Stop all schedulers"""
        for scheduler in self.schedulers.values():
            scheduler.stop_scheduler()
        self.logger.info("Stopped all schedulers")


# Utility functions for easy integration

def create_scheduler_for_user(user_id: str) -> DailyScheduler:
    """Create and configure a scheduler for a user"""
    return DailyScheduler(user_id)


async def run_scheduler_with_workflow(user_id: str, workflow_nodes: Dict[str, Callable]):
    """Run scheduler with workflow integration"""
    scheduler = DailyScheduler(user_id)
    scheduler.set_workflow_nodes(workflow_nodes)
    
    try:
        await scheduler.start_scheduler()
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
        logging.info("Scheduler stopped by user")