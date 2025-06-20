from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import json
import os
from utils.timezone_helper import get_local_time_naive


@dataclass
class DailyPlan:
    content: str
    metadata: Dict[str, Any]
    
    @classmethod
    def create(cls, content: str, update_source: str = "system") -> 'DailyPlan':
        return cls(
            content=content,
            metadata={
                "created": get_local_time_naive().isoformat(),
                "last_updated": get_local_time_naive().isoformat(),
                "update_source": update_source
            }
        )
    
    def update(self, new_content: str, update_source: str = "system") -> 'DailyPlan':
        self.content = new_content
        self.metadata.update({
            "last_updated": get_local_time_naive().isoformat(),
            "update_source": update_source
        })
        return self


@dataclass
class UserProfile:
    user_id: str
    name: str
    age: int
    condition: str
    goals: List[str]
    preferences: Dict[str, Any]
    patterns: Dict[str, Any]
    created_at: str
    last_updated: str
    
    @classmethod
    def create_default(cls, user_id: str = "alex") -> 'UserProfile':
        return cls(
            user_id=user_id,
            name="Alex",
            age=30,
            condition="ADHD-C",
            goals=[
                "Improve time awareness",
                "Better executive function",
                "Gentle awareness nudging"
            ],
            preferences={
                "communication_style": "gentle",
                "reminder_frequency": "moderate",
                "focus_areas": ["time_awareness", "task_transitions"],
                "timezone": "America/Los_Angeles"  # User's timezone
            },
            patterns={
                "active_hours": {"start": "07:00", "end": "22:00"},
                "check_in_preferences": ["morning", "midday", "evening"],
                "common_struggles": ["time_blindness", "task_switching", "hyperfocus"]
            },
            created_at=get_local_time_naive().isoformat(),
            last_updated=get_local_time_naive().isoformat()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        return cls(**data)


@dataclass
class User:
    profile: UserProfile
    current_plan: Optional[DailyPlan] = None
    plan_history: List[DailyPlan] = None
    
    def __post_init__(self):
        if self.plan_history is None:
            self.plan_history = []
    
    @classmethod
    def load_or_create(cls, user_id: str = "alex") -> 'User':
        profile_path = f"data/users/{user_id}/profile.json"
        
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                profile_data = json.load(f)
            profile = UserProfile.from_dict(profile_data)
        else:
            profile = UserProfile.create_default(user_id)
            cls._ensure_user_directory(user_id)
            cls._save_profile(profile)
        
        return cls(profile=profile)
    
    def save(self):
        self._save_profile(self.profile)
        if self.current_plan:
            self._save_current_plan()
    
    def update_preference(self, key: str, value: Any) -> bool:
        """Update a user preference and save"""
        try:
            self.profile.preferences[key] = value
            self.profile.last_updated = get_local_time_naive().isoformat()
            self.save()
            return True
        except Exception as e:
            print(f"Error updating preference {key}: {e}")
            return False
    
    def update_schedule_preference(self, phase: str, new_time: str) -> bool:
        """Update schedule preferences (future feature)"""
        # This could allow the agent to suggest and update schedule times
        schedule_prefs = self.profile.preferences.get("schedule_times", {})
        schedule_prefs[phase] = new_time
        return self.update_preference("schedule_times", schedule_prefs)
    
    def update_plan(self, content: str, update_source: str = "system"):
        if self.current_plan:
            self.current_plan.update(content, update_source)
        else:
            self.current_plan = DailyPlan.create(content, update_source)
        
        self._save_current_plan()
    
    def archive_current_plan(self):
        if self.current_plan:
            self.plan_history.append(self.current_plan)
            self.current_plan = None
    
    @staticmethod
    def _ensure_user_directory(user_id: str):
        user_dir = f"data/users/{user_id}"
        plans_dir = f"{user_dir}/plans"
        os.makedirs(plans_dir, exist_ok=True)
    
    @staticmethod
    def _save_profile(profile: UserProfile):
        profile_path = f"data/users/{profile.user_id}/profile.json"
        with open(profile_path, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
    
    def _save_current_plan(self):
        if self.current_plan:
            plan_path = f"data/users/{self.profile.user_id}/plans/current.json"
            with open(plan_path, 'w') as f:
                json.dump({
                    "content": self.current_plan.content,
                    "metadata": self.current_plan.metadata
                }, f, indent=2)