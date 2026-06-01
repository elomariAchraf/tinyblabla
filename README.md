# tinyblabla

Local AI writing assistant powered by **Mistral 7B**, running entirely on your Mac — no internet required after the first model download.

Two modes are available: an interactive terminal REPL and a system-wide background daemon.

---

## Features

- **Sentence reformulation** — rewrites any sentence with better grammar and style, returning multiple suggestions
- **Interactive REPL** — type sentences directly in the terminal and get corrections instantly
- **System-wide daemon** — works in any app (browser, editor, notes…) via a global keyboard shortcut
- **Native popup** — choose a suggestion from a macOS picker dialog, it replaces your original sentence in place
- **Fully local** — Mistral 7B runs on your machine, nothing leaves your computer

---

## Requirements

- macOS
- Python 3.9
- ~14 GB of free disk space (model weights)

---

## Quick start

```bash
git clone https://github.com/elomariAchraf/tinyblabla.git
cd tinyblabla
make setup   # create venv and install dependencies (once)
make run     # start the system-wide daemon
```

The model downloads automatically from HuggingFace on first run.

---

## macOS permissions

The daemon listens to global keyboard events and controls the keyboard to select/paste text. Grant these two permissions to your Terminal app:

- **System Settings → Privacy & Security → Accessibility** — required for the global hotkey and keyboard control
- **System Settings → Privacy & Security → Automation** — required for switching focus back to the original app

---

## Commands

| Command | Description |
|---|---|
| `make setup` | Create the virtual environment and install all dependencies |
| `make run` | Start the system-wide reformulation daemon |
| `make repl` | Start the interactive terminal REPL |

---

## Usage

### Daemon (system-wide)

1. Run `make run` — the model loads and the daemon listens in the background
2. In **any app**, place your cursor anywhere in a sentence
3. Press **Ctrl+Shift+Space**
4. Wait a few seconds while the model generates suggestions
5. A native macOS popup appears — click a suggestion to replace your original sentence in place

Type `exit` and press Enter in the terminal to stop the daemon.

### Interactive REPL

```bash
make repl
```

Type any sentence and get reformulated versions instantly. Type `exit` to quit.

```
You: This is a bad writed sentence.

Reformulated:
1. This is a poorly written sentence.
2. This sentence contains grammatical errors.
3. There are mistakes in this sentence.
```

---

## Files

| File | Description |
|---|---|
| `interrogate_mistral.py` | Interactive REPL |
| `reformulate_daemon.py` | Background hotkey daemon |
| `popup_worker.py` | Native macOS suggestion picker (spawned by the daemon) |
| `start.sh` | Activates the venv and starts the daemon |
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
