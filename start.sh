#!/bin/bash

# Personal AI Assistant Startup Script

echo "🚀 Starting Personal AI Assistant..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❓ Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
if ! python3 -c "import langgraph, openai, telegram" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install --upgrade pip
    pip install langgraph openai python-telegram-bot python-dotenv typing-extensions
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Check environment variables
echo "🔐 Checking environment variables..."
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Please create it with:"
    echo "TELEGRAM_TOKEN=your-telegram-bot-token"
    echo "OPENAI_API_KEY=your-openai-api-key" 
    echo "TELEGRAM_CHAT_ID=your-telegram-chat-id"
    echo "TAVILY_API_KEY=your-tavily-api-key"
    exit 1
fi

# Run the assistant
echo "🤖 Starting the Personal AI Assistant..."
python3 main.py