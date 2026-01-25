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
echo "$SCRIPT_DIR"
cd "$SCRIPT_DIR"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

echo -e "${YELLOW}🔄 Stopping existing bot processes...${NC}"
PIDS=$(pgrep -f "python.*main\.py" || true)
if [[ -n "$PIDS" ]]; then
  kill -9 $PIDS || true
  sleep 2
else
  echo -e "${YELLOW}ℹ️  No existing bot process found.${NC}"
fi

echo -e "${YELLOW}📥 Pulling latest changes from GitHub...${NC}"
git pull origin main
echo -e "${GREEN}✅ Successfully pulled latest changes${NC}"

if git diff --name-only ORIG_HEAD HEAD | grep -q "^requirements\.txt$"; then
  echo -e "${YELLOW}📦 requirements.txt changed, updating dependencies...${NC}"
  "$SCRIPT_DIR/.venv/bin/pip" install -r requirements.txt
  echo -e "${GREEN}✅ Dependencies updated${NC}"
fi

echo -e "${YELLOW}🚀 Starting bot...${NC}"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
nohup "$PYTHON" main.py > bot.log 2>&1 &
BOT_PID=$!

sleep 3
if ps -p "$BOT_PID" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Bot started successfully (PID: $BOT_PID)${NC}"
  echo -e "${BLUE}📝 Logs are being written to bot.log${NC}"
else
  echo -e "${RED}❌ Failed to start bot${NC}"
  echo -e "${YELLOW}📋 Check bot.log for error details${NC}"
  tail -n 50 bot.log || true
  exit 1
fi