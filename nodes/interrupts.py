from typing import Dict, Any
from datetime import datetime
import logging
from openai import AsyncOpenAI
from models.agent_state import AgentState
from models.user import User
from prompts.system_prompt import get_system_prompt
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_openai_client():
    """Get OpenAI client with proper error handling"""
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def handle_interrupt(state: AgentState, user_message: str) -> AgentState:
    """Handle interrupt messages while preserving context"""
    logger.info(f"Handling interrupt in phase: {state['current_phase']}")
    
    user = User.load_or_create(state["user_context"]["user_id"])
    
    # Save current context
    state["user_context"]["interrupt_context"] = {
        "interrupted_phase": state["current_phase"],
        "timestamp": datetime.now().isoformat(),
        "message": user_message
    }
    
    try:
        # Get system prompt for consistent identity
        system_prompt = get_system_prompt(user.profile)
        
        # Create context-aware response
        context_info = f"Current phase: {state['current_phase']}"
        if state.get("daily_plan"):
            context_info += f"\nToday's plan: {state['daily_plan']['content']}"
        
        client = get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{system_prompt}\n\nContext: {context_info}"},
                {"role": "user", "content": user_message}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        response_content = response.choices[0].message.content
        
        # Add to message history
        state["messages"].extend([
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
                "phase": state["current_phase"],
                "interrupt": True
            },
            {
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.now().isoformat(),
                "phase": state["current_phase"],
                "interrupt": True
            }
        ])
        
        # Update last activity
        state["last_activity"] = datetime.now()
        
        logger.info("Interrupt handled successfully")
        
    except Exception as e:
        logger.error(f"Error handling interrupt: {e}")
        fallback_message = "I hear you! I'm here to support you. Can you tell me more about what you need right now?"
        
        state["messages"].extend([
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
                "phase": state["current_phase"],
                "interrupt": True
            },
            {
                "role": "assistant",
                "content": fallback_message,
                "timestamp": datetime.now().isoformat(),
                "phase": state["current_phase"],
                "interrupt": True,
                "error": True
            }
        ])
    
    return state


async def resume_from_interrupt(state: AgentState) -> AgentState:
    """Resume normal flow after handling an interrupt"""
    logger.info("Resuming from interrupt")
    
    interrupt_context = state["user_context"].get("interrupt_context")
    
    if interrupt_context:
        logger.info(f"Resuming phase: {interrupt_context['interrupted_phase']}")
        # Clear interrupt context
        state["user_context"]["interrupt_context"] = None
        state["interrupt_flag"] = False
    
    return state


def should_interrupt(state: AgentState, user_message: str) -> bool:
    """Determine if a message should be treated as an interrupt"""
    # For now, any user message during an active phase is considered an interrupt
    # Later this could be enhanced with intent detection
    
    urgent_keywords = ['help', 'urgent', 'emergency', 'stuck', 'overwhelmed', 'anxiety', 'panic']
    
    # Check for urgent keywords
    message_lower = user_message.lower()
    has_urgent_keyword = any(keyword in message_lower for keyword in urgent_keywords)
    
    # Always interrupt for urgent messages
    if has_urgent_keyword:
        return True
    
    # Allow interruption during check-ins for natural conversation
    check_in_phases = ['morning_checkin', 'midday_checkin', 'evening_checkin']
    if state['current_phase'] in check_in_phases:
        return True
    
    # Default to allowing interruptions for flexibility
    return True