# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local AI writing assistant running entirely on macOS (Apple Silicon). Press **Ctrl+Shift+Space** in any app to reformulate the selected text using a local Mistral-7B model. Supports English and French. Two backends: fast MLX (recommended) and PyTorch/MPS.

## Environment Setup

```bash
source venv/bin/activate
```

The virtualenv uses Python 3.9 and includes: `torch`, `transformers`, `accelerate`, `safetensors`, `tokenizers`, `pynput`, `mlx-lm`, `pytest`.

## Running

**MLX daemon (recommended):**
```bash
make run-mlx
```

**PyTorch daemon:**
```bash
make run
```

**Tests:**
```bash
make test
```

Models download from HuggingFace on first run (~3.8 GB for MLX, ~14 GB for PyTorch). Type `exit` to stop the daemon.

## Project Structure

```
tinyblabla/          # shared logic package (no heavy imports)
  language.py        # detect_language() — accent chars + French function words
  parser.py          # parse_suggestions(), stream_parse(), clean_segment()
daemons/             # long-running daemon entry points
  reformulate_daemon_mlx.py   # MLX backend (stream_generate, streaming popup)
  reformulate_daemon.py       # PyTorch/MPS backend (batch generate, loader spinner)
ui/                  # UI subprocesses spawned by the daemons
  stream_popup.py    # native AppKit window, fills in suggestions as they stream in
  loader_worker.py   # instant borderless spinner shown while model generates
  popup_worker.py    # legacy AppleScript picker (used by PyTorch daemon)
tests/
  test_language.py   # unit tests for detect_language
  test_parser.py     # unit tests for parse_suggestions, clean_segment
  test_integration.py # integration tests: full pipeline, streaming vs batch
```

## Architecture

- **Language detection** (`tinyblabla/language.py`) — detects French via accented characters or ≥2 French function words; falls back to English. Used by both daemons to build language-explicit prompts.

- **Parsing** (`tinyblabla/parser.py`) — `parse_suggestions` handles batch output; `stream_parse(chunks)` is a generator that yields each suggestion as soon as the next numbered item begins, enabling the streaming popup.

- **MLX daemon** — calls `stream_parse` over `mlx_lm.stream_generate` output; pipes suggestions line-by-line to `stream_popup.py` via stdin. The popup process is launched before generation starts so its ~0.14s startup overlaps with the clipboard grab.

- **PyTorch daemon** — batch generation with `transformers`; spawns `loader_worker.py` as an instant spinner during generation, then `popup_worker.py` to show the AppleScript picker.

- **Subprocess path resolution** — both daemons use `_ROOT = pathlib.Path(__file__).resolve().parent.parent` to locate `ui/` workers regardless of where Python is invoked from. Shell scripts set `PYTHONPATH=.` so the `tinyblabla` package is found.

- **launchd** — the MLX daemon is registered as a LaunchAgent at `~/Library/LaunchAgents/com.tinyblabla.daemon.plist`, which starts it at login via `start_mlx.sh`.