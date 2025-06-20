"""
Timezone helper for deployment environments
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz


# Pacific timezone
PACIFIC_TZ = pytz.timezone('America/Los_Angeles')


def set_timezone_for_deployment():
    """Set timezone for cloud deployment environments"""
    # Most cloud platforms run in UTC by default
    # Set timezone to Pacific for consistent ADHD assistant timing
    target_timezone = os.getenv('TZ', 'America/Los_Angeles')
    
    if target_timezone != os.environ.get('TZ'):
        os.environ['TZ'] = target_timezone
        try:
            import time
            time.tzset()  # Apply timezone change (Unix systems)
        except (AttributeError, OSError):
            # Windows or some cloud platforms don't support tzset
            pass


def get_user_timezone(user_id: str = "alex") -> pytz.BaseTzInfo:
    """Get user's timezone from their profile"""
    try:
        from models.user import User
        user = User.load_or_create(user_id)
        timezone_str = user.profile.preferences.get("timezone", "America/Los_Angeles")
        return pytz.timezone(timezone_str)
    except Exception:
        # Fallback to Pacific if we can't load user profile
        return PACIFIC_TZ


def get_local_time(user_id: str = "alex") -> datetime:
    """Get current time in user's timezone"""
    utc_now = datetime.now(timezone.utc)
    user_tz = get_user_timezone(user_id)
    local_time = utc_now.astimezone(user_tz)
    return local_time


def get_local_time_naive(user_id: str = "alex") -> datetime:
    """Get current time in user's timezone as naive datetime (for compatibility)"""
    return get_local_time(user_id).replace(tzinfo=None)


def format_time_for_user(dt: Optional[datetime] = None) -> str:
    """Format time in user-friendly way"""
    if dt is None:
        dt = get_local_time()
    
    # Determine if we're in PDT or PST
    is_dst = dt.dst() != timedelta(0) if hasattr(dt, 'dst') and dt.tzinfo else True
    tz_name = "PDT" if is_dst else "PST"
    
    return dt.strftime(f"%H:%M {tz_name}")


# Set timezone on import for deployment
set_timezone_for_deployment()