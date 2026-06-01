# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local AI writing assistant powered by [Mistral-7B-Instruct-v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3), running on Mac using HuggingFace Transformers. Includes an interactive REPL and a system-wide reformulation daemon.

## Environment Setup

```bash
source venv/bin/activate
```

The virtualenv uses Python 3.9 and includes: `torch`, `transformers`, `accelerate`, `safetensors`, `tokenizers`, `pynput`.

## Running

**REPL:**
```bash
python interrogate_mistral.py
```

**Daemon:**
```bash
bash start.sh
```

The model downloads from HuggingFace on first run (~14GB). Subsequent runs load from cache. Type `exit` to stop either mode.

## Architecture

- `interrogate_mistral.py` — interactive REPL for sentence reformulation
- `reformulate_daemon.py` — background daemon, listens for Ctrl+Shift+Space globally, grabs the current sentence, runs Mistral 7B, shows a native macOS popup, and replaces the sentence in place
- `popup_worker.py` — subprocess spawned by the daemon to show an AppleScript `choose from list` dialog (avoids Cocoa main-thread conflicts with tkinter)
- Model uses `torch.float16` on MPS (Apple Silicon GPU) or CPU
