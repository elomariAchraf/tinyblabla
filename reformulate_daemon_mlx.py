"""
MLX-accelerated reformulation daemon.
Uses Apple MLX backend with a 4-bit quantized Mistral-7B model for fast
inference with strong multilingual support (English, French, and more).

Requirements: pip install mlx-lm
Model: ~3.8 GB download on first run (mlx-community/Mistral-7B-Instruct-v0.3-4bit)
"""
import json
import logging
import re
import subprocess
import sys
import time
import threading
from mlx_lm import load, generate as mlx_generate
from pynput import keyboard

HOTKEY = "<ctrl>+<shift>+<space>"
MODEL_NAME = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
LOG_FILE = "reformulate.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

log.info("Loading %s via MLX...", MODEL_NAME)
model, tokenizer = load(MODEL_NAME)
log.info("Model loaded. Hotkey active: Ctrl+Shift+Space")

kb = keyboard.Controller()
_busy = threading.Lock()

_FRENCH_WORDS = frozenset([
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "le", "la", "les", "un", "une", "des", "du", "de", "et",
    "est", "sont", "que", "qui", "dans", "sur", "avec", "pour",
    "par", "mais", "ou", "donc", "ni", "car", "pas", "ne", "se",
])

def detect_language(text):
    import re
    if re.search(r'[çœàâùûîïêëôéèæ]', text.lower()):
        return "French"
    words = set(re.findall(r'\b\w+\b', text.lower()))
    if len(words & _FRENCH_WORDS) >= 2:
        return "French"
    return "English"


_NUM_RE = re.compile(r"^\s*(\d{1,2})[.)]\s+(.*)$")


def parse_suggestions(raw):
    """Extract numbered reformulations from raw model output.

    Joins wrapped continuation lines into a single suggestion and drops any
    preamble or trailing commentary that falls outside the numbered list.
    """
    suggestions = []
    current = None
    for line in raw.splitlines():
        m = _NUM_RE.match(line)
        if m:
            if current is not None:
                suggestions.append(current.strip())
            current = m.group(2)
        elif current is not None:
            if line.strip() == "":
                # A blank line ends the current item; trailing commentary that
                # follows it (and isn't numbered) is ignored.
                suggestions.append(current.strip())
                current = None
            else:
                # Continuation of a soft-wrapped suggestion line.
                current += " " + line.strip()
    if current is not None:
        suggestions.append(current.strip())
    return [s for s in suggestions if s][:5]


def reformulate(sentence):
    log.debug("Reformulating: %r", sentence)
    lang = detect_language(sentence)
    log.debug("Detected language: %s", lang)
    messages = [{
        "role": "user",
        "content": (
            f"Rewrite the {lang} text below with better grammar and style. "
            "Give 5 alternative versions. Each version must be a COMPLETE rewrite "
            "of the ENTIRE text, preserving every sentence and all information — "
            "do not drop or summarize any part. "
            f"Your response MUST be entirely in {lang}; do not translate. "
            "Output ONLY the 5 versions as a numbered list (1. through 5.), one "
            "per line. Do not add any preamble, explanation, or commentary.\n\n"
            f"Text:\n{sentence}"
        ),
    }]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    start = time.perf_counter()
    raw = mlx_generate(model, tokenizer, prompt=prompt, max_tokens=600, verbose=False)
    elapsed = time.perf_counter() - start
    log.debug("Raw model output: %r", raw)
    result = parse_suggestions(raw)
    log.info("%d suggestion(s) generated in %.2fs", len(result), elapsed)
    return result


def clipboard_read():
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout

def clipboard_write(text):
    subprocess.run(["pbcopy"], input=text, text=True)

def paste_text(text):
    log.info("Pasting chosen text: %r", text)
    clipboard_write(text)
    time.sleep(0.05)
    with kb.pressed(keyboard.Key.cmd):
        kb.press("v")
        kb.release("v")

def get_frontmost_app():
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to get name of first application process whose frontmost is true'],
        capture_output=True, text=True,
    )
    return result.stdout.strip()

def activate_app(name):
    log.debug("Refocusing app: %s", name)
    subprocess.run(
        ["osascript", "-e", f'tell application "{name}" to activate'],
        capture_output=True, text=True,
    )
    time.sleep(0.15)

# Sentinel placed on the clipboard to detect whether the user already has an
# active text selection: Cmd+C overwrites it only if something was selected.
_NO_SELECTION = "\x00__tinyblabla_no_selection__\x00"

def copy_selection():
    with kb.pressed(keyboard.Key.cmd):
        kb.press("c")
        kb.release("c")
    time.sleep(0.1)

def select_line():
    with kb.pressed(keyboard.Key.cmd):
        with kb.pressed(keyboard.Key.shift):
            kb.press(keyboard.Key.left)
            kb.release(keyboard.Key.left)
    time.sleep(0.08)

def grab_sentence():
    """Grab the user's current selection (any length, multi-line included).

    If nothing is selected, fall back to selecting the current line. In both
    cases the selection stays active so the chosen suggestion can be pasted
    straight over it later.
    """
    clipboard_write(_NO_SELECTION)
    time.sleep(0.05)
    copy_selection()
    grabbed = clipboard_read()
    if grabbed == _NO_SELECTION or grabbed == "":
        log.debug("No selection detected; selecting current line")
        select_line()
        copy_selection()
        grabbed = clipboard_read()
    else:
        log.debug("Using existing selection (%d chars)", len(grabbed))
    return grabbed.strip()


def handle_hotkey():
    if not _busy.acquire(blocking=False):
        log.warning("Already processing, hotkey ignored")
        return
    original_clipboard = clipboard_read()
    try:
        log.info("Hotkey triggered — grabbing sentence")
        source_app = get_frontmost_app()
        log.debug("Source app: %s", source_app)

        sentence = grab_sentence()
        log.debug("Sentence grabbed: %r", sentence)
        if not sentence:
            log.warning("Nothing selected and current line is empty — aborting")
            return

        # Pop a loading spinner instantly so the user gets feedback while the
        # model generates (which takes a couple of seconds).
        workdir = __file__[:__file__.rfind("/")]
        loader = subprocess.Popen([sys.executable, "loader_worker.py"], cwd=workdir)
        try:
            suggestions = reformulate(sentence)
        finally:
            loader.terminate()
            try:
                loader.wait(timeout=2)
            except Exception:
                loader.kill()
        if not suggestions:
            log.warning("No suggestions returned by the model")
            return

        log.info("Opening popup with %d suggestion(s)", len(suggestions))
        result = subprocess.run(
            [sys.executable, "popup_worker.py", json.dumps(suggestions)],
            capture_output=True,
            text=True,
            cwd=workdir,
        )
        if result.stderr.strip():
            log.error("popup_worker stderr:\n%s", result.stderr.strip())
        log.debug("popup_worker returncode: %d", result.returncode)
        chosen = result.stdout.strip()
        if chosen:
            # The grabbed block is still selected in the source app, so a single
            # paste replaces the whole selection — multi-line included.
            activate_app(source_app)
            paste_text(chosen)
        else:
            log.info("Popup closed without selection")
    except Exception:
        log.exception("Unexpected error in handle_hotkey")
    finally:
        time.sleep(0.2)
        clipboard_write(original_clipboard)
        _busy.release()


def on_hotkey():
    threading.Thread(target=handle_hotkey, daemon=True).start()


def _stdin_watcher(stop_event):
    log.info("Type 'exit' to stop the daemon")
    for line in sys.stdin:
        if line.strip().lower() == "exit":
            log.info("Shutdown requested — stopping...")
            stop_event.set()
            break


def main():
    log.info("Starting global hotkey listener (hotkey: %s)", HOTKEY)
    stop_event = threading.Event()
    threading.Thread(target=_stdin_watcher, args=(stop_event,), daemon=True).start()

    with keyboard.GlobalHotKeys({HOTKEY: on_hotkey}) as listener:
        stop_event.wait()
        listener.stop()
    log.info("Daemon stopped.")


if __name__ == "__main__":
    main()
