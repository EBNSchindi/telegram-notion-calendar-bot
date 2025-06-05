#!/bin/bash
# Script to run the bot with proper environment

# Activate virtual environment
source venv/bin/activate

# Run the bot
echo "🤖 Starting Telegram Bot..."
echo "Bot name: @notionassistantDS_bot"
echo "Press Ctrl+C to stop"
echo ""

python src/bot.py