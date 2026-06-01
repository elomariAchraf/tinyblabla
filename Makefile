SHELL := /bin/bash

.PHONY: setup run repl

setup:
	bash setup.sh

run:
	bash start.sh

repl:
	source venv/bin/activate && python interrogate_mistral.py
