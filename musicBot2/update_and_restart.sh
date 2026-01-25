#!/usr/bin/env bash

# Update and restart script for musicBot2
# This script will pull the latest changes from GitHub and restart the bot
# Designed to work with systemd service management

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}🔄 Starting bot update and restart process...${NC}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    echo "FAILED"
    exit 1
fi

# Check disk space (at least 100MB free)
AVAILABLE_MB=$(df -m "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
if [[ "$AVAILABLE_MB" -lt 100 ]]; then
    echo -e "${RED}❌ Error: Low disk space (${AVAILABLE_MB}MB available)${NC}"
    echo "FAILED"
    exit 1
fi

# Check if there are uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}⚠️  Warning: There are uncommitted changes. Stashing them...${NC}"
    git stash push -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)"
fi

# Save current commit for rollback
PREV_COMMIT=$(git rev-parse HEAD)
echo -e "${YELLOW}📌 Current commit: ${PREV_COMMIT:0:8}${NC}"

# Pull latest changes
echo -e "${YELLOW}📥 Pulling latest changes from GitHub...${NC}"
if ! git pull origin main; then
    echo -e "${RED}❌ Git pull failed${NC}"
    echo "FAILED"
    exit 1
fi

NEW_COMMIT=$(git rev-parse HEAD)
echo -e "${GREEN}✅ Updated to commit: ${NEW_COMMIT:0:8}${NC}"

# Check if requirements.txt changed
if git diff --name-only "$PREV_COMMIT" HEAD | grep -q "^requirements\.txt$"; then
    echo -e "${YELLOW}📦 requirements.txt changed, updating dependencies...${NC}"
    if [[ -f "$SCRIPT_DIR/.venv/bin/pip" ]]; then
        "$SCRIPT_DIR/.venv/bin/pip" install -r requirements.txt --quiet
        echo -e "${GREEN}✅ Dependencies updated${NC}"
    else
        echo -e "${YELLOW}⚠️  Virtual environment not found, skipping dependency update${NC}"
    fi
fi

# Show what changed
echo -e "${BLUE}📝 Changes:${NC}"
git log --oneline "$PREV_COMMIT..$NEW_COMMIT" 2>/dev/null | head -10 || echo "No new commits"

# Restart via systemd
echo -e "${YELLOW}🚀 Restarting bot via systemd...${NC}"
if ! sudo systemctl restart musicbot2; then
    echo -e "${RED}❌ Failed to restart bot${NC}"
    
    # Attempt rollback
    echo -e "${YELLOW}🔙 Attempting rollback to ${PREV_COMMIT:0:8}...${NC}"
    git checkout "$PREV_COMMIT"
    
    if sudo systemctl restart musicbot2; then
        echo -e "${YELLOW}⚠️  Rolled back to previous version${NC}"
        echo "ROLLBACK"
        exit 1
    else
        echo -e "${RED}❌ Rollback also failed!${NC}"
        echo "FAILED"
        exit 1
    fi
fi

# Wait and verify the bot started
echo -e "${YELLOW}⏳ Waiting for bot to start...${NC}"
sleep 5

if sudo systemctl is-active --quiet musicbot2; then
    echo -e "${GREEN}✅ Bot started successfully!${NC}"
    
    # Show service status
    echo -e "${BLUE}📊 Service status:${NC}"
    sudo systemctl status musicbot2 --no-pager | head -20
    
    echo "SUCCESS"
else
    echo -e "${RED}❌ Bot failed to start after update${NC}"
    
    # Show recent logs
    echo -e "${YELLOW}📋 Recent logs:${NC}"
    sudo journalctl -u musicbot2 -n 20 --no-pager
    
    # Attempt rollback
    echo -e "${YELLOW}🔙 Attempting rollback to ${PREV_COMMIT:0:8}...${NC}"
    git checkout "$PREV_COMMIT"
    
    if sudo systemctl restart musicbot2 && sleep 3 && sudo systemctl is-active --quiet musicbot2; then
        echo -e "${YELLOW}⚠️  Rolled back to previous version${NC}"
        echo "ROLLBACK"
    else
        echo -e "${RED}❌ Rollback also failed - manual intervention required${NC}"
        echo "FAILED"
    fi
    
    exit 1
fi
