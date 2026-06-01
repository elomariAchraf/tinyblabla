# tinyblabla

Local AI writing assistant running entirely on your Mac — no internet required after the first model download.

Two backends are available: a fast **MLX** daemon (recommended) powered by Phi-3 Mini 4-bit, and a standard **PyTorch/MPS** daemon powered by Mistral-7B-Instruct-v0.3.

Two modes are available: a system-wide background daemon and an interactive terminal REPL.

---

## Features

- **Sentence reformulation** — rewrites any selected text with better grammar and style, returning 3 suggestions
- **System-wide daemon** — works in any app (browser, editor, notes…) via a global keyboard shortcut
- **Native popup** — choose a suggestion from a macOS picker dialog, it replaces your original text in place
- **Interactive REPL** — type sentences directly in the terminal and get reformulations instantly
- **Two backends** — fast MLX (Apple-native, 4-bit quantized) or full-precision PyTorch/MPS
- **Fully local** — everything runs on your machine, nothing leaves your computer

---

## Requirements

- macOS 13.5+ (Apple Silicon)
- Python 3.9+
- Disk space: ~2.3 GB (MLX / Phi-3 Mini) or ~14 GB (PyTorch / Mistral 7B)

---

## Quick start

```bash
git clone https://github.com/elomariAchraf/tinyblabla.git
cd tinyblabla
make setup        # create venv and install base dependencies (run once)
make setup-mlx    # install mlx-lm for the fast backend (run once)
make run-mlx      # start the fast MLX daemon (recommended)
```

The model downloads automatically from HuggingFace on first run.

---

## Backends

### MLX (recommended)

Uses Apple's [MLX](https://github.com/ml-explore/mlx) framework with `mlx-community/Phi-3-mini-4k-instruct-4bit`.

- **2–4× faster** than the PyTorch daemon
- **~2.3 GB** model download (vs ~14 GB for Mistral 7B)
- Optimized natively for Apple Silicon

```bash
make setup-mlx   # one-time: installs mlx-lm
make run-mlx     # start the MLX daemon
```

### PyTorch / MPS (original)

Uses `transformers` + PyTorch MPS with `mistralai/Mistral-7B-Instruct-v0.3`.

Includes these performance optimizations over the original:
- `torch.compile(mode="reduce-overhead")` applied at startup with a warmup inference
- `max_new_tokens` reduced from 120 → 80
- Shorter prompt to reduce prefill time
- `@torch.inference_mode()` on the generation function

```bash
make run         # start the PyTorch daemon
```

---

## macOS permissions

The daemon listens to global keyboard events and controls the keyboard to select/paste text. Grant these two permissions to your Terminal app:

- **System Settings → Privacy & Security → Accessibility** — required for the global hotkey and keyboard control
- **System Settings → Privacy & Security → Automation** — required for switching focus back to the original app after the popup closes

---

## Commands

| Command | Description |
|---|---|
| `make setup` | Create the virtual environment and install base dependencies |
| `make setup-mlx` | Install `mlx-lm` for the fast MLX backend |
| `make run-mlx` | Start the fast MLX daemon (Phi-3 Mini, recommended) |
| `make run` | Start the PyTorch/MPS daemon (Mistral 7B) |
| `make repl` | Start the interactive terminal REPL |

> **Note:** `make repl` must be run directly in your own terminal — it requires an interactive session.

---

## Usage

### Daemon (system-wide)

1. Run `make run-mlx` — the model loads and the daemon listens in the background
2. In **any app**, place your cursor anywhere in a sentence
3. Press **Ctrl+Shift+Space**
4. A native macOS popup appears with 3 suggestions — click one to replace your original text in place

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

| Package | Version | Used by |
|---|---|---|
| Python | 3.9.6 | both |
| mlx | 0.29.3 | MLX daemon |
| mlx-lm | 0.29.1 | MLX daemon |
| torch | 2.8.0 | PyTorch daemon |
| transformers | 4.57.6 | PyTorch daemon |
| accelerate | 1.10.1 | PyTorch daemon |
| tokenizers | 0.22.2 | PyTorch daemon |
| safetensors | 0.7.0 | PyTorch daemon |
| sentencepiece | 0.2.1 | both |
| pynput | 1.8.2 | both |

---

## Files

| File | Description |
|---|---|
| `reformulate_daemon_mlx.py` | Fast MLX daemon (Phi-3 Mini 4-bit, recommended) |
| `reformulate_daemon.py` | PyTorch/MPS daemon (Mistral 7B) |
| `interrogate_mistral.py` | Interactive REPL |
| `popup_worker.py` | Native macOS suggestion picker (spawned by the daemon) |
| `start_mlx.sh` | Activates the venv and starts the MLX daemon |
| `start.sh` | Activates the venv and starts the PyTorch daemon |
| `repl.sh` | Activates the venv and starts the REPL |
| `setup.sh` | One-time setup: creates venv and installs base dependencies |
| `requirements.txt` | Python dependencies |
| `Makefile` | Shortcuts: `setup`, `setup-mlx`, `run`, `run-mlx`, `repl` |

---

## Logs

The daemon writes a log file at `reformulate.log` in the project directory. To follow events live:

```bash
tail -f reformulate.log
```

Log levels: `INFO` for main events, `DEBUG` for raw model output, `WARNING` for skipped inputs or busy state, `ERROR` for unexpected failures.
