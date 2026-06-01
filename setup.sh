#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Creating virtual environment..."
python -m venv venv

echo "Installing dependencies..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt

echo ""
echo "Setup complete. Run the daemon with: make run"
echo "Or the interactive REPL with:        make repl"
