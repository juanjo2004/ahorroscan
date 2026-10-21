#!/bin/bash
set -euo pipefail
cd /home/debian/ahorroscan/test/current/telegram-bot-v2
exec flock -n /tmp/ahorroscan_pet.lock venv/bin/python run_pet.py >> /home/debian/ahorroscan/test/current/telegram-bot-v2/logs/pet_runner.log 2>&1