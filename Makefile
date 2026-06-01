SHELL := /bin/bash

.PHONY: setup run run-mlx setup-mlx repl

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
