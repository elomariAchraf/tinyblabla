SHELL := /bin/bash

.PHONY: setup run run-mlx setup-mlx repl test

setup:
	bash setup.sh

setup-mlx:
	venv/bin/pip install mlx-lm

run:
	bash start.sh

run-mlx:
	bash start_mlx.sh

repl:
	bash repl.sh

test:
	venv/bin/pip install -q pytest && venv/bin/pytest tests/ -v
