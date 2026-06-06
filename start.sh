#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
PYTHONPATH=. python daemons/reformulate_daemon.py
