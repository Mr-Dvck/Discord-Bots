#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo "  JAMIE DISCORD BOT - Starting..."
echo "════════════════════════════════════════"
echo ""

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "[!] Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "[*] Starting Jamie..."
python main.py
