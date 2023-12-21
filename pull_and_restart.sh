#!/usr/bin/env bash

ps -ef | grep musicBot.py | grep -v "grep" | awk '{print $2}' | xargs kill
git pull
python3 musicBot.py &> musicBot.log