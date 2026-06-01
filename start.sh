#!/bin/bash
cd "$(dirname "$0")"
source tinyllama_env/bin/activate
python reformulate_daemon.py
