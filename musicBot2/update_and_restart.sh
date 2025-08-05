#!/usr/bin/env bash

# Update and restart script for musicBot2
# This script will pull the latest changes from GitHub and restart the bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Starting bot update and restart process...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Check if there are any uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes. Consider committing them first.${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Update cancelled${NC}"
        exit 1
    fi
fi

# Kill existing bot processes
echo -e "${YELLOW}🔄 Stopping existing bot processes...${NC}"
pkill -f "python.*main.py" || true
pkill -f "python.*musicBot2" || true

# Wait a moment for processes to stop
sleep 2

# Pull latest changes from GitHub
echo -e "${YELLOW}📥 Pulling latest changes from GitHub...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✅ Successfully pulled latest changes${NC}"
else
    echo -e "${RED}❌ Failed to pull changes from GitHub${NC}"
    exit 1
fi

# Check if requirements.txt has changed and update dependencies if needed
if git diff --name-only HEAD~1 HEAD | grep -q "requirements.txt"; then
    echo -e "${YELLOW}📦 Requirements.txt changed, updating dependencies...${NC}"
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
        echo -e "${GREEN}✅ Dependencies updated${NC}"
    else
        echo -e "${YELLOW}⚠️  pip3 not found, skipping dependency update${NC}"
    fi
fi

# Start the bot in the background
echo -e "${YELLOW}🚀 Starting bot...${NC}"
nohup python3 main.py > bot.log 2>&1 &
BOT_PID=$!

# Wait a moment and check if the bot started successfully
sleep 3
if ps -p $BOT_PID > /dev/null; then
    echo -e "${GREEN}✅ Bot started successfully (PID: $BOT_PID)${NC}"
    echo -e "${BLUE}📝 Logs are being written to bot.log${NC}"
else
    echo -e "${RED}❌ Failed to start bot${NC}"
    echo -e "${YELLOW}📋 Check bot.log for error details${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Bot update and restart completed successfully!${NC}" 