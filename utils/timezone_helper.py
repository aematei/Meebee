"""
Timezone helper for deployment environments
"""
import os
from datetime import datetime
from typing import Optional


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


def get_local_time() -> datetime:
    """Get current time in the configured timezone"""
    return datetime.now()


def format_time_for_user(dt: Optional[datetime] = None) -> str:
    """Format time in user-friendly way"""
    if dt is None:
        dt = datetime.now()
    
    return dt.strftime("%H:%M PDT")


# Set timezone on import for deployment
set_timezone_for_deployment()