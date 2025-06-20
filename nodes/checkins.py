from typing import Dict, Any
from datetime import datetime
import logging
from openai import AsyncOpenAI
from models.agent_state import AgentState
from models.user import User
from prompts.phase_prompts import get_phase_prompt
from utils.google_calendar import create_google_calendar_manager
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def morning_checkin(state: AgentState) -> AgentState:
    """Morning check-in node - gentle start to the day"""
    logger.info("Executing morning check-in")
    
    user = User.load_or_create(state["user_context"]["user_id"])
    
    # Get phase-specific prompt
    prompt = get_phase_prompt("morning_checkin", user.profile, state.get("context_data", {}))
    
    try:
        # Include current plan in context
        current_plan = state.get("daily_plan", {}).get("content", "No plan set yet")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Good morning! Here's today's plan: {current_plan}. How are you feeling about starting the day?"}
            ],
            max_tokens=300,
            temperature=0.8
        )
        
        checkin_content = response.choices[0].message.content
        
        # Update state
        state["current_phase"] = "midday_checkin"
        state["last_activity"] = datetime.now()
        state["messages"].append({
            "role": "assistant",
            "content": checkin_content,
            "timestamp": datetime.now().isoformat(),
            "phase": "morning_checkin"
        })
        
        logger.info("Morning check-in completed successfully")
        
    except Exception as e:
        logger.error(f"Error in morning check-in: {e}")
        fallback_message = "Good morning! How are you feeling as we start the day? Remember, we're taking things one step at a time."
        
        state["messages"].append({
            "role": "assistant",
            "content": fallback_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "morning_checkin",
            "error": True
        })
    
    return state


async def midday_checkin(state: AgentState) -> AgentState:
    """Midday check-in node - gentle awareness nudge"""
    logger.info("Executing midday check-in")
    
    user = User.load_or_create(state["user_context"]["user_id"])
    
    # Get calendar context for next events
    calendar_manager = create_google_calendar_manager(user.profile.user_id)
    next_event = calendar_manager.get_next_event()
    
    # Update context data
    context_data = state.get("context_data", {})
    context_data["next_event"] = next_event
    state["context_data"] = context_data
    
    # Get phase-specific prompt
    prompt = get_phase_prompt("midday_checkin", user.profile, context_data)
    
    try:
        # Include current plan and next event in context
        current_plan = state.get("daily_plan", {}).get("content", "No plan set")
        
        next_event_info = ""
        if next_event:
            if next_event['is_all_day']:
                next_event_info = f"\n\nBy the way, you have '{next_event['summary']}' today."
            else:
                next_event_time = next_event['start_time'].strftime("%H:%M")
                next_event_info = f"\n\nBy the way, you have '{next_event['summary']}' coming up at {next_event_time}."
        
        user_message = f"It's midday! Here's what we planned: {current_plan}. How's your day going so far?{next_event_info}"
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.8
        )
        
        checkin_content = response.choices[0].message.content
        
        # Update state
        state["current_phase"] = "evening_checkin"
        state["last_activity"] = datetime.now()
        state["messages"].append({
            "role": "assistant",
            "content": checkin_content,
            "timestamp": datetime.now().isoformat(),
            "phase": "midday_checkin"
        })
        
        logger.info("Midday check-in completed successfully")
        
    except Exception as e:
        logger.error(f"Error in midday check-in: {e}")
        fallback_message = "Hello! Just checking in at midday. How are you doing? Remember to take breaks and be kind to yourself."
        
        state["messages"].append({
            "role": "assistant",
            "content": fallback_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "midday_checkin",
            "error": True
        })
    
    return state


async def evening_checkin(state: AgentState) -> AgentState:
    """Evening check-in node - wind down and reflect"""
    logger.info("Executing evening check-in")
    
    user = User.load_or_create(state["user_context"]["user_id"])
    
    # Get phase-specific prompt
    prompt = get_phase_prompt("evening_checkin", user.profile, state.get("context_data", {}))
    
    try:
        # Include current plan in context
        current_plan = state.get("daily_plan", {}).get("content", "No plan was set")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Good evening! Here's what we planned today: {current_plan}. How did your day go?"}
            ],
            max_tokens=300,
            temperature=0.8
        )
        
        checkin_content = response.choices[0].message.content
        
        # Update state
        state["current_phase"] = "nighttime_planning"
        state["last_activity"] = datetime.now()
        state["messages"].append({
            "role": "assistant",
            "content": checkin_content,
            "timestamp": datetime.now().isoformat(),
            "phase": "evening_checkin"
        })
        
        logger.info("Evening check-in completed successfully")
        
    except Exception as e:
        logger.error(f"Error in evening check-in: {e}")
        fallback_message = "Good evening! How was your day? Take a moment to appreciate what you accomplished, no matter how small."
        
        state["messages"].append({
            "role": "assistant",
            "content": fallback_message,
            "timestamp": datetime.now().isoformat(),
            "phase": "evening_checkin",
            "error": True
        })
    
    return state