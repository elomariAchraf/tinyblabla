# tinyblabla

Local AI writing assistant powered by **Mistral-7B-Instruct-v0.3**, running entirely on your Mac — no internet required after the first model download.

Two modes are available: a system-wide background daemon and an interactive terminal REPL.

---

## Features

- **Sentence reformulation** — rewrites any selected text with better grammar and style, returning 3 suggestions
- **System-wide daemon** — works in any app (browser, editor, notes…) via a global keyboard shortcut
- **Native popup** — choose a suggestion from a macOS picker dialog, it replaces your original text in place
- **Interactive REPL** — type sentences directly in the terminal and get reformulations instantly
- **Apple Silicon GPU** — runs on MPS (Metal) for faster inference, falls back to CPU automatically
- **Fully local** — Mistral 7B runs on your machine, nothing leaves your computer

---

## Requirements

- macOS
- Python 3.9+
- ~14 GB of free disk space (model weights)

---

## Quick start

```bash
git clone https://github.com/elomariAchraf/tinyblabla.git
cd tinyblabla
make setup   # create venv and install all dependencies (run once)
make run     # start the system-wide daemon
```

The model downloads automatically from HuggingFace on first run.

---

## macOS permissions

The daemon listens to global keyboard events and controls the keyboard to select/paste text. Grant these two permissions to your Terminal app:

- **System Settings → Privacy & Security → Accessibility** — required for the global hotkey and keyboard control
- **System Settings → Privacy & Security → Automation** — required for switching focus back to the original app after the popup closes

---

## Commands

| Command | Description |
|---|---|
| `make setup` | Create the virtual environment and install all dependencies |
| `make run` | Start the system-wide reformulation daemon |
| `make repl` | Start the interactive terminal REPL |

> **Note:** `make repl` must be run directly in your own terminal — it requires an interactive session.

---

## Usage

### Daemon (system-wide)

1. Run `make run` — the model loads onto the GPU and the daemon listens in the background
2. In **any app**, place your cursor anywhere in a sentence
3. Press **Ctrl+Shift+Space**
4. Wait a few seconds while the model generates suggestions
5. A native macOS popup appears — click a suggestion to replace your original text in place

Type `exit` and press Enter in the terminal to stop the daemon.

### Interactive REPL

Run `make repl` in your terminal, then type any sentence and press Enter:

```
You: This is a bad writed sentence.

Reformulated:
1. This is a poorly written sentence.
2. This sentence contains grammatical errors.
3. There are mistakes in this sentence.
```

Type `exit` to quit.

---

## Stack

| Package | Version |
|---|---|
| Python | 3.9.6 |
| torch | 2.8.0 |
| transformers | 4.57.6 |
| accelerate | 1.10.1 |
| tokenizers | 0.22.2 |
| safetensors | 0.7.0 |
| sentencepiece | 0.2.1 |
| pynput | 1.8.2 |

---

## Files

| File | Description |
|---|---|
| `interrogate_mistral.py` | Interactive REPL |
| `reformulate_daemon.py` | Background hotkey daemon |
| `popup_worker.py` | Native macOS suggestion picker (spawned by the daemon) |
| `start.sh` | Activates the venv and starts the daemon |
| `repl.sh` | Activates the venv and starts the REPL |
| `setup.sh` | One-time setup: creates venv and installs dependencies |
| `requirements.txt` | Python dependencies |
| `Makefile` | Shortcuts: `setup`, `run`, `repl` |

---

## Logs

The daemon writes a log file at `reformulate.log` in the project directory. To follow events live:

```bash
tail -f reformulate.log
```

Log levels: `INFO` for main events, `DEBUG` for raw model output, `WARNING` for skipped inputs or busy state, `ERROR` for unexpected failures.
