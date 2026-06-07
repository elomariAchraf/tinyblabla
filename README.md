# tinyblabla

Local AI writing assistant running entirely on your Mac — no internet required after the first model download.

Two backends are available: a fast **MLX** daemon (recommended) powered by Mistral-7B 4-bit, and a standard **PyTorch/MPS** daemon powered by Mistral-7B full-precision.

---

## Features

- **Sentence reformulation** — rewrites any selected text with better grammar and style, returning 5 suggestions
- **Multilingual** — detects English and French automatically and responds in the same language
- **Streaming popup** — suggestions appear one by one as the model generates them, no waiting for all 5
- **System-wide daemon** — works in any app (browser, editor, notes…) via a global keyboard shortcut
- **Native popup** — choose a suggestion from a macOS picker dialog, it replaces your original text in place
- **Two backends** — fast MLX (Apple-native, 4-bit quantized) or full-precision PyTorch/MPS
- **Fully local** — everything runs on your machine, nothing leaves your computer

---

## Requirements

- macOS 13.5+ (Apple Silicon)
- Python 3.9+
- Disk space: ~3.8 GB (MLX / Mistral 7B 4-bit) or ~14 GB (PyTorch / Mistral 7B full)

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

Uses Apple's [MLX](https://github.com/ml-explore/mlx) framework with `mlx-community/Mistral-7B-Instruct-v0.3-4bit`.

- **2–4× faster** than the PyTorch daemon
- **~3.8 GB** model download (vs ~14 GB for the full-precision daemon)
- Suggestions stream into the popup one by one as they are generated
- Optimized natively for Apple Silicon

```bash
make setup-mlx   # one-time: installs mlx-lm
make run-mlx     # start the MLX daemon
```

### PyTorch / MPS

Uses `transformers` + PyTorch MPS with `mistralai/Mistral-7B-Instruct-v0.3`.

- `torch.compile(mode="reduce-overhead")` applied at startup with a warmup inference
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
| `make run-mlx` | Start the fast MLX daemon (Mistral 7B 4-bit, recommended) |
| `make run` | Start the PyTorch/MPS daemon (Mistral 7B full-precision) |
| `make test` | Run the unit and integration test suite |

---

## Usage

1. Run `make run-mlx` — the model loads and the daemon listens in the background
2. In **any app**, place your cursor in a sentence or select a block of text
3. Press **Ctrl+Shift+Space**
4. A native macOS popup appears instantly with a spinner, then fills in with suggestions as they stream in
5. Click a suggestion (or press its number key) to replace your original text in place

Type `exit` and press Enter in the terminal to stop the daemon.

### Example — English

```
Input:  This is a bad writed sentence.

1. This is a poorly written sentence.
2. This sentence contains grammatical errors.
3. There are several mistakes in this sentence.
4. The sentence is grammatically incorrect.
5. This sentence was written incorrectly.
```

### Example — French

```
Input:  Je veux que tu viens avec moi demain.

1. Je voudrais que tu viennes avec moi demain.
2. J'aimerais que tu m'accompagnes demain.
3. Pourrais-tu venir avec moi demain ?
4. Je souhaite ta présence avec moi demain.
5. Est-ce que tu peux venir avec moi demain ?
```

---

## Project structure

```
tinyblabla/          # shared logic package
  language.py        # language detection (English / French)
  parser.py          # suggestion parsing: batch, streaming, segment cleaning
daemons/             # long-running background processes
  reformulate_daemon_mlx.py   # MLX backend (recommended)
  reformulate_daemon.py       # PyTorch/MPS backend
ui/                  # UI subprocesses spawned by the daemons
  stream_popup.py    # streaming AppKit suggestion picker
  loader_worker.py   # instant loading spinner
  popup_worker.py    # legacy AppleScript picker (PyTorch daemon)
tests/               # unit and integration tests
start_mlx.sh / start.sh      # venv activation + daemon launch
setup.sh             # one-time venv and dependency setup
```

---

## Tests

```bash
make test
```

Covers language detection, suggestion parsing (batch and streaming), and end-to-end pipeline integration with realistic model outputs in English and French.

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
| pytest | 8.4.2 | tests |

---

## Logs

The daemon writes a log file at `reformulate.log` in the project directory. To follow events live:

```bash
tail -f reformulate.log
```

Log levels: `INFO` for main events, `DEBUG` for raw model output and detected language, `WARNING` for skipped inputs or busy state, `ERROR` for unexpected failures.
