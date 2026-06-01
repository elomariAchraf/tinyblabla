#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python interrogate_mistral.py
