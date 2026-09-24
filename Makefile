SHELL := /bin/bash

.PHONY: setup run run-mlx setup-mlx run-claude setup-claude run-openai setup-openai repl test

setup:
	bash setup.sh

setup-mlx:
	venv/bin/pip install mlx-lm

setup-claude:
	venv/bin/pip install anthropic

setup-openai:
	venv/bin/pip install openai

run:
	bash start.sh

run-mlx:
	bash start_mlx.sh

run-claude:
	bash start_claude.sh

run-openai:
	bash start_openai.sh

repl:
	bash repl.sh

test:
	venv/bin/pip install -q pytest && venv/bin/pytest tests/ -v
