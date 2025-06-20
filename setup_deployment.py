#!/usr/bin/env python3
"""
Setup script for cloud deployment
Ensures data directories exist and handles initial setup
"""
import os
from pathlib import Path
import json


def ensure_data_directories():
    """Ensure all required data directories exist"""
    base_dirs = [
        "data/users/alex",
        "data/users/alex/plans"
    ]
    
    for dir_path in base_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")


def create_default_user_profile():
    """Create default user profile if it doesn't exist"""
    profile_path = Path("data/users/alex/profile.json")
    
    if not profile_path.exists():
        from models.user import UserProfile
        
        profile = UserProfile.create_default("alex")
        profile_data = profile.to_dict()
        
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        print("✅ Created default user profile")
    else:
        print("✅ User profile already exists")


def check_environment_variables():
    """Check that all required environment variables are set"""
    required_vars = [
        "TELEGRAM_TOKEN",
        "OPENAI_API_KEY", 
        "TELEGRAM_CHAT_ID",
        "TAVILY_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    else:
        print("✅ All environment variables present")
        return True


def setup_google_calendar_placeholder():
    """Create placeholder for Google Calendar credentials"""
    creds_path = Path("data/users/alex/google_credentials.json")
    
    if not creds_path.exists():
        # Create placeholder file with instructions
        placeholder = {
            "note": "Replace this file with your actual Google OAuth credentials",
            "instructions": [
                "1. Go to Google Cloud Console",
                "2. Enable Calendar API", 
                "3. Create OAuth 2.0 credentials",
                "4. Download the JSON file",
                "5. Replace this file with the downloaded credentials"
            ]
        }
        
        with open(creds_path, 'w') as f:
            json.dump(placeholder, f, indent=2)
        
        print("⚠️  Created Google Calendar credentials placeholder")
        print(f"   Replace {creds_path} with your actual OAuth credentials")
    else:
        print("✅ Google Calendar credentials file exists")


def main():
    """Run deployment setup"""
    print("🚀 Setting up Personal AI Assistant for deployment")
    print("=" * 60)
    
    # Ensure directories exist
    ensure_data_directories()
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Create user profile
    create_default_user_profile()
    
    # Setup calendar placeholder
    setup_google_calendar_placeholder()
    
    print("\n" + "=" * 60)
    
    if env_ok:
        print("✅ Deployment setup complete!")
        print("\nNext steps:")
        print("1. Push to GitHub")
        print("2. Deploy to Railway.app")
        print("3. Set environment variables in Railway dashboard")
        print("4. Upload Google Calendar credentials (if needed)")
        print("5. Test with /schedule command in Telegram")
    else:
        print("⚠️  Setup complete, but environment variables need to be configured")
        print("\nSet these in your deployment platform:")
        print("- TELEGRAM_TOKEN")
        print("- OPENAI_API_KEY") 
        print("- TELEGRAM_CHAT_ID")
        print("- TAVILY_API_KEY")


if __name__ == "__main__":
    main()