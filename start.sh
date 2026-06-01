#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python reformulate_daemon.py
