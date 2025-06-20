# Personal AI Assistant for ADHD-C

A gentle, supportive AI assistant that provides awareness nudging throughout the day using LangGraph state management and Telegram integration.

## 🎯 Purpose

Designed specifically for someone with ADHD-C, this assistant focuses on:
- **Gentle awareness nudging** rather than productivity optimization
- **Time awareness and executive function support**
- **Daily cycle check-ins** with natural conversation flow
- **Context switching interrupt handling**

## 🏗️ Architecture

- **LangGraph**: State machine with 5 daily cycle nodes
- **Telegram Bot**: Primary communication interface  
- **OpenAI GPT**: Natural language processing
- **User Profiles**: Learning patterns over time
- **Persistent Plans**: Single mutable plan structure

### Daily Cycle Flow
```
morning_planning → morning_checkin → midday_checkin → evening_checkin → nighttime_planning → (repeat)
```

## 🚀 Quick Start

### Option 1: Using the startup script
```bash
./start.sh
```

### Option 2: Manual setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install langgraph openai python-telegram-bot python-dotenv typing-extensions

# Run the assistant
python3 main.py
```

## ⚙️ Configuration

Create a `.env` file with your API keys:
```env
TELEGRAM_TOKEN=your-telegram-bot-token
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_CHAT_ID=your-telegram-chat-id
TAVILY_API_KEY=your-tavily-api-key
```

## 📁 Project Structure

```
/
├── .env                    # Environment variables
├── main.py                 # Main application entry point
├── start.sh                # Startup script
├── requirements.txt        # Python dependencies
├── models/
│   ├── user.py            # User, UserProfile, DailyPlan classes
│   └── agent_state.py     # LangGraph state schema
├── nodes/
│   ├── planning.py        # Morning/nighttime planning nodes
│   ├── checkins.py        # Daily check-in nodes
│   └── interrupts.py      # Interrupt handling
├── prompts/
│   ├── system_prompt.py   # Core assistant identity
│   └── phase_prompts.py   # Phase-specific prompts
├── utils/
│   ├── telegram_bot.py    # Telegram integration
│   ├── google_calendar.py # Google Calendar integration
│   └── scheduler.py       # Daily cycle scheduling and automatic nudges
└── data/
    └── users/
        └── alex/
            ├── profile.json    # User profile data
            └── plans/          # Daily plans history
```

## 🧪 Testing

### Quick Setup Validation
```bash
python3 validate_setup.py
```

### Test Commands
```bash
# Install test dependencies and run validation
python3 run_tests.py --install-deps --validate

# Run unit tests only
python3 run_tests.py --unit

# Run fast tests (excluding slow external service tests and telegram tests)
python3 run_tests.py --fast

# Run all tests
python3 run_tests.py --all

# Run tests with coverage report
python3 run_tests.py --coverage

# Run specific test categories
python3 run_tests.py --calendar    # Google Calendar tests
python3 run_tests.py --telegram    # Telegram bot tests
python3 run_tests.py --integration # Integration tests
```

### Test Structure
```
tests/
├── conftest.py           # Shared fixtures and test utilities
├── unit/                 # Unit tests for individual components
│   ├── test_models.py   # User, DailyPlan, AgentState tests
│   └── test_google_calendar.py # Calendar integration tests
└── integration/         # Integration tests
    ├── test_workflow.py # LangGraph workflow tests
    └── test_telegram_bot.py # Telegram bot integration tests
```

### Test Features
- **Mock External Services**: Tests don't require actual Telegram/OpenAI/Calendar access
- **Isolated Testing**: Each test runs in isolation with fresh state
- **Async Support**: Full async/await testing support
- **Fixtures**: Reusable test data and mock objects
- **Coverage Reporting**: HTML and terminal coverage reports
- **CI Ready**: Structured for automated testing environments

## 🤖 User Context

**Target User**: Alex, 30yo with ADHD-C
- **Challenges**: Time blindness, executive function, hyperfocus
- **Goals**: Gentle awareness improvement, not productivity maximization
- **Approach**: Supportive companion, not rigid scheduler

## 🔧 Core Features

### 1. **LangGraph State Machine**
- 5-node daily cycle with natural transitions
- Persistent state with memory checkpoints
- Context-aware phase transitions

### 2. **Telegram Integration**
- Real-time bidirectional communication
- Command support (`/status`, `/plan`, `/help`)
- Interrupt handling during conversations

### 3. **Google Calendar Integration**
- Automatic calendar event awareness
- Context-aware planning around appointments
- Gentle transition reminders for upcoming events
- Calendar commands for quick schedule overview

### 4. **Daily Scheduler**
- Automatic phase transitions at scheduled times
- Gentle awareness nudges with customizable timing
- Grace periods for natural transition flexibility
- Background monitoring without being intrusive

### 5. **Gentle Awareness System**
- Phase-specific prompts for each daily stage
- Flexible, non-judgmental communication
- Celebration of small wins

### 6. **User Learning**
- Profile evolution based on interaction patterns
- Daily plan history and reflection
- Personalized prompt adaptation

## 📱 Usage

### Commands
- `/start` - Initialize the assistant
- `/help` - Show available commands  
- `/status` - Check current phase and activity
- `/plan` - View today's plan

**Calendar Commands:**
- `/calendar` - Calendar overview (today + tomorrow)
- `/today` - Today's events
- `/next` - Next upcoming event
- `/calendar_setup` - Instructions for Google Calendar setup

**Scheduler Commands:**
- `/schedule` - View current schedule status and daily timing
- `/start_scheduler` - Enable automatic gentle nudges at scheduled times
- `/stop_scheduler` - Disable automatic nudges (manual mode)

### Daily Flow
1. **Morning Planning**: Create gentle day structure
2. **Morning Check-in**: Ease into the day
3. **Midday Check-in**: Awareness nudge and support
4. **Evening Check-in**: Day reflection and wind-down
5. **Nighttime Planning**: Closure and tomorrow preview

## 🔄 Interrupt Handling

The assistant can handle context switches at any time:
- Saves current state and context
- Responds to immediate needs
- Resumes normal flow when appropriate
- Prioritizes urgent keywords (help, stuck, overwhelmed)

## 🎨 Design Principles

1. **Gentle Approach**: Never pushy or demanding
2. **Awareness Over Productivity**: Focus on mindful awareness
3. **Compassionate Understanding**: ADHD-specific challenges
4. **Flexibility**: Adapt to user's current state
5. **Celebration**: Acknowledge all progress

## 🚧 Future Enhancements

- Multi-user support expansion
- Advanced scheduling integration
- Pattern analysis and insights
- Voice message support
- Web dashboard interface

## 📝 Development Notes

- Hardcoded for `user_id="alex"` but structured for expansion
- Uses OpenAI GPT-4o-mini for cost efficiency
- Memory-based checkpointing for state persistence
- Modular design for easy feature additions

---

**Built with care for neurodivergent users** 💙