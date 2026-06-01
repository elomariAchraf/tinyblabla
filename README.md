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

## Setup

```bash
python3.9 -m venv tinyllama_env
source tinyllama_env/bin/activate
pip install torch transformers accelerate safetensors tokenizers pynput
```

The model is downloaded automatically from HuggingFace on first run.

### macOS permissions

The daemon listens to global keyboard events and controls the keyboard to select/paste text. Grant these two permissions to your Terminal app:

- **System Settings → Privacy & Security → Accessibility** — add Terminal (required for global hotkey and keyboard control)
- **System Settings → Privacy & Security → Automation** — allow Terminal to control other apps (required for `osascript` focus switching)

---

## Usage

### Interactive REPL

```bash
source tinyllama_env/bin/activate
python interrogate_mistral.py
```

Type a sentence ending with a `.` and press Enter. The model returns several reformulated versions. Type `exit`, `quit`, or `bye` to stop.

```
Vous : This is a bad writed sentence.

Corrigé :
1. This is a poorly written sentence.
2. This sentence contains grammatical errors.
...
```

### System-wide daemon

```bash
bash start.sh
```

Or make it executable once and run directly:

```bash
chmod +x start.sh
./start.sh
```

1. The daemon loads the model and listens in the background
2. In **any app**, place your cursor at the end of a sentence that ends with `.`
3. Press **Ctrl+Shift+Space**
4. Wait ~20 seconds while the model generates suggestions
5. A native macOS popup appears — click a suggestion or use keyboard navigation
6. The chosen text **replaces** your original sentence in place

To stop the daemon, type `exit` and press Enter in the terminal where it is running.

---

## Files

| File | Description |
|---|---|
| `interrogate_mistral.py` | Interactive REPL |
| `reformulate_daemon.py` | Background hotkey daemon |
| `popup_worker.py` | Native macOS suggestion picker (spawned by the daemon) |
| `start.sh` | Activates the venv and starts the daemon |

---

## Logs

The daemon writes a log file at `reformulate.log` in the project directory. To follow events live:

```bash
tail -f reformulate.log
```

Log levels: `INFO` for main events, `DEBUG` for raw model output, `WARNING` for skipped inputs or busy state, `ERROR` for unexpected failures.
