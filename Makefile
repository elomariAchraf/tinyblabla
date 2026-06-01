SHELL := /bin/bash

.PHONY: setup run repl

setup:
	bash setup.sh

run:
	bash start.sh

repl:
	bash repl.sh
