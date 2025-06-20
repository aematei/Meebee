from typing import Dict, Any
from datetime import datetime
import logging
from openai import AsyncOpenAI
from models.agent_state import AgentState, create_daily_plan, update_daily_plan
from models.user import User
from prompts.phase_prompts import get_phase_prompt
from utils.google_calendar import create_google_calendar_manager
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_openai_client():
    """Get OpenAI client with proper error handling"""
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def morning_planning(state: AgentState) -> AgentState:
    """Morning planning node - creates or updates the daily plan"""
    logger.info("Executing morning planning")
    
    user = User.load_or_create(state["user_context"]["user_id"])
    
    # Get calendar context
    calendar_manager = create_google_calendar_manager(user.profile.user_id)
    calendar_context = calendar_manager.get_calendar_context_for_planning()
    
    # Add calendar context to state context_data
    context_data = state.get("context_data", {})
    context_data.update(calendar_context)
    state["context_data"] = context_data
    
    # Get phase-specific prompt with calendar context
    prompt = get_phase_prompt("morning_planning", user.profile, context_data)
    
    try:
        # Include calendar information in the planning message
        calendar_info = ""
        if calendar_context["has_calendar_access"] and calendar_context["today_events"]:
            calendar_info = f"\n\nToday's calendar:\n{calendar_context['calendar_summary']}"
        elif calendar_context["has_calendar_access"]:
            calendar_info = "\n\nYour calendar is clear today!"
        
        user_message = f"Let's create a gentle plan for today. What should I focus on?{calendar_info}"
        
        client = get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        plan_content = response.choices[0].message.content
        
        # Create or update daily plan
        if state["daily_plan"]:
            updated_plan = update_daily_plan(state["daily_plan"], plan_content, "morning_planning")
        else:
            updated_plan = create_daily_plan(plan_content, "morning_planning")
        
        # Update user's plan
        user.update_plan(plan_content, "morning_planning")
        user.save()
        
        # Update state
        state["daily_plan"] = updated_plan
        state["current_phase"] = "morning_checkin"
        state["last_activity"] = datetime.now()
        state["messages"].append({
            "role": "assistant",
            "content": plan_content,
            "timestamp": datetime.now().isoformat(),
            "phase": "morning_planning"
        })
        
        logger.info("Morning planning completed successfully")
        
    except Exception as e:
        logger.error(f"Error in morning planning: {e}")
        fallback_message = "Good morning! Let's start with a gentle approach to today. What's one thing you'd like to focus on?"
        
        state["messages"].append({
            "role": "assistant",
            "content": fallback_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "morning_planning",
            "error": True
        })
    
    return state


async def nighttime_planning(state: AgentState) -> AgentState:
    """Nighttime planning node - reflects on the day and prepares for tomorrow"""
    logger.info("Executing nighttime planning")
    
    user = User.load_or_create(state["user_context"]["user_id"])
    
    # Get phase-specific prompt
    prompt = get_phase_prompt("nighttime_planning", user.profile, state.get("context_data", {}))
    
    try:
        # Include today's plan in the context for reflection
        today_plan = state.get("daily_plan", {}).get("content", "No plan was set today")
        
        client = get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Here's what I planned for today: {today_plan}. Let's reflect on the day and prepare for tomorrow."}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        reflection_content = response.choices[0].message.content
        
        # Archive current plan and prepare for tomorrow
        user.archive_current_plan()
        user.save()
        
        # Update state
        state["current_phase"] = "morning_planning"  # Reset for next day
        state["last_activity"] = datetime.now()
        state["daily_plan"] = None  # Clear for fresh start tomorrow
        state["messages"].append({
            "role": "assistant",
            "content": reflection_content,
            "timestamp": datetime.now().isoformat(),
            "phase": "nighttime_planning"
        })
        
        logger.info("Nighttime planning completed successfully")
        
    except Exception as e:
        logger.error(f"Error in nighttime planning: {e}")
        fallback_message = "Thank you for a good day. Rest well, and we'll start fresh tomorrow!"
        
        state["messages"].append({
            "role": "assistant",
            "content": fallback_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "nighttime_planning",
            "error": True
        })
    
    return state