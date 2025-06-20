"""
Unit tests for core model classes
"""
import pytest
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from models.user import User, UserProfile, DailyPlan
from models.agent_state import (
    AgentState, create_initial_state, create_daily_plan, update_daily_plan
)


class TestUserProfile:
    """Test UserProfile class"""
    
    def test_create_default_profile(self):
        """Test creating default user profile"""
        profile = UserProfile.create_default("test_user")
        
        assert profile.user_id == "test_user"
        assert profile.name == "Alex"
        assert profile.age == 30
        assert profile.condition == "ADHD-C"
        assert "Improve time awareness" in profile.goals
        assert profile.preferences["communication_style"] == "gentle"
        assert "time_awareness" in profile.preferences["focus_areas"]
    
    def test_profile_to_dict_conversion(self):
        """Test profile serialization"""
        profile = UserProfile.create_default("test_user")
        profile_dict = profile.to_dict()
        
        assert isinstance(profile_dict, dict)
        assert profile_dict["user_id"] == "test_user"
        assert profile_dict["name"] == "Alex"
        assert "created_at" in profile_dict
    
    def test_profile_from_dict_conversion(self):
        """Test profile deserialization"""
        original_profile = UserProfile.create_default("test_user")
        profile_dict = original_profile.to_dict()
        restored_profile = UserProfile.from_dict(profile_dict)
        
        assert restored_profile.user_id == original_profile.user_id
        assert restored_profile.name == original_profile.name
        assert restored_profile.age == original_profile.age
        assert restored_profile.goals == original_profile.goals


class TestDailyPlan:
    """Test DailyPlan class"""
    
    @freeze_time("2024-01-15 10:30:00")
    def test_create_daily_plan(self):
        """Test creating a daily plan"""
        content = "Focus on gentle awareness today"
        plan = DailyPlan.create(content, "test_source")
        
        assert plan.content == content
        assert plan.metadata["update_source"] == "test_source"
        assert plan.metadata["created"] == "2024-01-15T10:30:00"
        assert plan.metadata["last_updated"] == "2024-01-15T10:30:00"
    
    @freeze_time("2024-01-15 10:30:00")
    def test_update_daily_plan(self):
        """Test updating a daily plan"""
        plan = DailyPlan.create("Original plan", "morning_planning")
        
        with freeze_time("2024-01-15 14:30:00"):
            updated_plan = plan.update("Updated plan content", "midday_checkin")
        
        assert updated_plan.content == "Updated plan content"
        assert updated_plan.metadata["created"] == "2024-01-15T10:30:00"
        assert updated_plan.metadata["last_updated"] == "2024-01-15T14:30:00"
        assert updated_plan.metadata["update_source"] == "midday_checkin"


class TestUser:
    """Test User class"""
    
    def test_user_initialization(self, sample_user_profile):
        """Test user initialization"""
        user = User(profile=sample_user_profile)
        
        assert user.profile == sample_user_profile
        assert user.current_plan is None
        assert user.plan_history == []
    
    def test_update_plan(self, sample_user_profile):
        """Test updating user plan"""
        with patch('models.user.User._save_current_plan'):  # Mock file operations
            user = User(profile=sample_user_profile)
            
            # First plan
            user.update_plan("First plan", "morning_planning")
            assert user.current_plan is not None
            assert user.current_plan.content == "First plan"
            
            # Update plan
            user.update_plan("Updated plan", "midday_checkin")
            assert user.current_plan.content == "Updated plan"
            assert user.current_plan.metadata["update_source"] == "midday_checkin"
    
    def test_archive_current_plan(self, sample_user_profile):
        """Test archiving current plan"""
        with patch('models.user.User._save_current_plan'):  # Mock file operations
            user = User(profile=sample_user_profile)
            
            # Create and archive a plan
            user.update_plan("Plan to archive", "morning_planning")
            current_plan = user.current_plan
            user.archive_current_plan()
            
            assert user.current_plan is None
            assert len(user.plan_history) == 1
            assert user.plan_history[0] == current_plan


class TestAgentState:
    """Test AgentState functionality"""
    
    def test_create_initial_state(self):
        """Test creating initial agent state"""
        state = create_initial_state("test_user")
        
        assert state["user_context"]["user_id"] == "test_user"
        assert state["current_phase"] == "morning_planning"
        assert state["interrupt_flag"] is False
        assert state["daily_plan"] is None
        assert state["messages"] == []
        assert isinstance(state["context_data"], dict)
    
    @freeze_time("2024-01-15 10:30:00")
    def test_create_daily_plan_state(self):
        """Test creating daily plan in state format"""
        content = "Today's gentle plan"
        plan = create_daily_plan(content, "morning_planning")
        
        assert plan["content"] == content
        assert plan["metadata"]["update_source"] == "morning_planning"
        assert plan["metadata"]["created"] == "2024-01-15T10:30:00"
    
    @freeze_time("2024-01-15 10:30:00")
    def test_update_daily_plan_state(self):
        """Test updating daily plan in state format"""
        original_plan = create_daily_plan("Original", "morning_planning")
        
        with freeze_time("2024-01-15 14:30:00"):
            updated_plan = update_daily_plan(original_plan, "Updated", "midday_checkin")
        
        assert updated_plan["content"] == "Updated"
        assert updated_plan["metadata"]["created"] == "2024-01-15T10:30:00"
        assert updated_plan["metadata"]["last_updated"] == "2024-01-15T14:30:00"
        assert updated_plan["metadata"]["update_source"] == "midday_checkin"


@pytest.mark.unit
class TestModelIntegration:
    """Test integration between models"""
    
    def test_user_with_agent_state_integration(self, sample_user_profile, temp_data_dir):
        """Test that user and agent state work together"""
        with patch('models.user.User._save_current_plan'):  # Mock file saving
            user = User(profile=sample_user_profile)
            state = create_initial_state(user.profile.user_id)
            
            # Update user plan
            user.update_plan("Integrated plan", "morning_planning")
            
            # Update state with plan
            state["daily_plan"] = create_daily_plan(
                user.current_plan.content, 
                "morning_planning"
            )
            
            assert state["daily_plan"]["content"] == "Integrated plan"
            assert state["user_context"]["user_id"] == user.profile.user_id