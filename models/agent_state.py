from typing import Dict, List, Optional, Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import add_messages
from datetime import datetime
import json


class DailyPlan(TypedDict):
    content: str
    metadata: Dict[str, Any]


class UserContext(TypedDict):
    user_id: str
    current_phase: str
    interrupt_context: Optional[Dict[str, Any]]


class AgentState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_context: UserContext
    daily_plan: Optional[DailyPlan]
    current_phase: str
    interrupt_flag: bool
    last_activity: Optional[datetime]
    context_data: Dict[str, Any]


def create_initial_state(user_id: str = "alex") -> AgentState:
    return AgentState(
        messages=[],
        user_context=UserContext(
            user_id=user_id,
            current_phase="morning_planning",
            interrupt_context=None
        ),
        daily_plan=None,
        current_phase="morning_planning",
        interrupt_flag=False,
        last_activity=None,
        context_data={}
    )


def create_daily_plan(content: str, update_source: str = "system") -> DailyPlan:
    return DailyPlan(
        content=content,
        metadata={
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "update_source": update_source
        }
    )


def update_daily_plan(plan: DailyPlan, new_content: str, update_source: str = "system") -> DailyPlan:
    return DailyPlan(
        content=new_content,
        metadata={
            **plan["metadata"],
            "last_updated": datetime.now().isoformat(),
            "update_source": update_source
        }
    )