import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Scopes required for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'data/users/alex/google_credentials.json'
TOKEN_FILE = 'data/users/alex/google_token.json'


class GoogleCalendarManager:
    def __init__(self, user_id: str = "alex"):
        self.user_id = user_id
        self.service = None
        self.credentials = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Set up Google Calendar API credentials"""
        creds = None
        token_path = f"data/users/{self.user_id}/google_token.json"
        credentials_path = f"data/users/{self.user_id}/google_credentials.json"
        
        # Check for environment variable credentials (for deployment)
        env_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if env_creds and not os.path.exists(credentials_path):
            try:
                # Create credentials file from environment variable
                import json
                os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
                with open(credentials_path, 'w') as f:
                    if env_creds.startswith('{'):
                        f.write(env_creds)
                    else:
                        # Handle base64 encoded or other formats
                        f.write(env_creds)
                logger.info("Created credentials file from environment variable")
            except Exception as e:
                logger.error(f"Error creating credentials from environment: {e}")
        
        # Load existing token
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid token file format: {e}, removing and re-authorizing")
                os.remove(token_path)
                creds = None
        
        # If there are no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if os.path.exists(credentials_path):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                        logger.info("Successfully completed OAuth flow")
                    except Exception as e:
                        logger.error(f"OAuth flow failed: {e}")
                        return
                else:
                    logger.warning(f"Google credentials file not found at {credentials_path}")
                    return
            
            # Save the credentials for the next run
            try:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info("Token saved successfully")
            except Exception as e:
                logger.error(f"Failed to save token: {e}")
        
        self.credentials = creds
        
        if creds:
            try:
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Google Calendar API service initialized")
            except Exception as e:
                logger.error(f"Error building calendar service: {e}")
        else:
            logger.warning("No valid Google Calendar credentials available")
    
    def is_available(self) -> bool:
        """Check if Google Calendar is available"""
        return self.service is not None
    
    def get_todays_events(self) -> List[Dict[str, Any]]:
        """Get today's calendar events"""
        if not self.service:
            logger.warning("Google Calendar service not available")
            return []
        
        try:
            # Get start and end of today
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events to extract relevant information
            processed_events = []
            for event in events:
                processed_event = self._process_event(event)
                if processed_event:
                    processed_events.append(processed_event)
            
            logger.info(f"Retrieved {len(processed_events)} events for today")
            return processed_events
            
        except HttpError as error:
            logger.error(f"An error occurred retrieving calendar events: {error}")
            return []
    
    def get_upcoming_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming events for the next specified hours"""
        if not self.service:
            logger.warning("Google Calendar service not available")
            return []
        
        try:
            now = datetime.now()
            end_time = now + timedelta(hours=hours)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            processed_events = []
            for event in events:
                processed_event = self._process_event(event)
                if processed_event:
                    processed_events.append(processed_event)
            
            logger.info(f"Retrieved {len(processed_events)} upcoming events")
            return processed_events
            
        except HttpError as error:
            logger.error(f"An error occurred retrieving upcoming events: {error}")
            return []
    
    def get_next_event(self) -> Optional[Dict[str, Any]]:
        """Get the next upcoming event"""
        upcoming = self.get_upcoming_events(hours=24)
        return upcoming[0] if upcoming else None
    
    def _process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a raw calendar event into a simplified format"""
        try:
            summary = event.get('summary', 'No title')
            
            # Handle different time formats
            start = event.get('start', {})
            end = event.get('end', {})
            
            # All-day events
            if 'date' in start:
                start_time = datetime.fromisoformat(start['date'])
                end_time = datetime.fromisoformat(end['date']) if 'date' in end else start_time
                is_all_day = True
            else:
                # Timed events
                start_datetime = start.get('dateTime', '')
                end_datetime = end.get('dateTime', '')
                
                if start_datetime:
                    start_time = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(end_datetime.replace('Z', '+00:00')) if end_datetime else start_time
                    is_all_day = False
                else:
                    return None
            
            return {
                'id': event.get('id'),
                'summary': summary,
                'description': event.get('description', ''),
                'start_time': start_time,
                'end_time': end_time,
                'is_all_day': is_all_day,
                'location': event.get('location', ''),
                'status': event.get('status', 'confirmed'),
                'url': event.get('htmlLink', ''),
                'duration_minutes': int((end_time - start_time).total_seconds() / 60) if not is_all_day else None
            }
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return None
    
    def format_events_for_display(self, events: List[Dict[str, Any]]) -> str:
        """Format events for display in chat"""
        if not events:
            return "No events found."
        
        formatted = []
        for event in events:
            if event['is_all_day']:
                time_str = "All day"
            else:
                start_str = event['start_time'].strftime("%H:%M")
                end_str = event['end_time'].strftime("%H:%M")
                time_str = f"{start_str} - {end_str}"
            
            event_str = f"• {time_str}: {event['summary']}"
            if event['location']:
                event_str += f" ({event['location']})"
            
            formatted.append(event_str)
        
        return "\n".join(formatted)
    
    def get_calendar_context_for_planning(self) -> Dict[str, Any]:
        """Get calendar context for daily planning"""
        today_events = self.get_todays_events()
        next_event = self.get_next_event()
        
        context = {
            'has_calendar_access': self.is_available(),
            'today_events_count': len(today_events),
            'today_events': today_events,
            'next_event': next_event,
            'calendar_summary': self.format_events_for_display(today_events) if today_events else "No events today"
        }
        
        return context


def create_google_calendar_manager(user_id: str = "alex") -> GoogleCalendarManager:
    """Factory function to create a Google Calendar manager"""
    return GoogleCalendarManager(user_id)


def setup_google_calendar_instructions() -> str:
    """Get instructions for setting up Google Calendar integration"""
    return """
To set up Google Calendar integration:

1. Go to the Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API
4. Create credentials (OAuth 2.0 Client ID for Desktop Application)
5. Download the credentials JSON file
6. Save it as: data/users/alex/google_credentials.json

The first time you run the calendar integration, it will open a browser window for you to authorize access to your calendar.
"""