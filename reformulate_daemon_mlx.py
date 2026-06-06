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
from mlx_lm import load, stream_generate
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


# Matches the start of a numbered list item ("1. ", "2) ", ...) at line start.
_NUM_START = re.compile(r"(?m)^\s*\d{1,2}[.)]\s")


def _clean_segment(seg):
    """Strip the leading number from one numbered item and collapse it to a
    single line, dropping any blank-line-separated trailing commentary."""
    seg = _NUM_START.sub("", seg, count=1)
    out = []
    for ln in seg.splitlines():
        if ln.strip() == "":
            break  # a blank line ends the item; ignore commentary after it
        out.append(ln.strip())
    return " ".join(out).strip()


def _build_prompt(sentence):
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
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def stream_reformulate(sentence):
    """Generate reformulations, yielding each completed numbered suggestion as
    soon as the next one begins — so the first result surfaces early instead of
    after the whole block finishes."""
    log.debug("Reformulating: %r", sentence)
    prompt = _build_prompt(sentence)
    buf = ""
    yielded = 0
    first = None
    start = time.perf_counter()
    for resp in stream_generate(model, tokenizer, prompt=prompt, max_tokens=600):
        buf += resp.text
        starts = [m.start() for m in _NUM_START.finditer(buf)]
        # An item is complete once the next numbered item has begun.
        while yielded + 1 < len(starts) and yielded < 5:
            text = _clean_segment(buf[starts[yielded]:starts[yielded + 1]])
            if text:
                if first is None:
                    first = time.perf_counter() - start
                yield text
            yielded += 1
        if yielded >= 5:
            break
    # Flush the final in-progress item once generation ends.
    if yielded < 5:
        starts = [m.start() for m in _NUM_START.finditer(buf)]
        if yielded < len(starts):
            text = _clean_segment(buf[starts[yielded]:])
            if text:
                if first is None:
                    first = time.perf_counter() - start
                yield text
                yielded += 1
    total = time.perf_counter() - start
    log.info(
        "%d suggestion(s) streamed; first in %.2fs, all in %.2fs",
        yielded, first if first is not None else total, total,
    )


def reformulate(sentence):
    """Non-streaming convenience wrapper (collects the stream into a list)."""
    return list(stream_reformulate(sentence))


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

        # Launch the popup first (it shows a spinner instantly), then stream
        # suggestions into it as they complete so the first one appears early.
        workdir = __file__[:__file__.rfind("/")]
        popup = subprocess.Popen(
            [sys.executable, "stream_popup.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            cwd=workdir,
        )
        count = 0
        try:
            for suggestion in stream_reformulate(sentence):
                count += 1
                try:
                    popup.stdin.write(suggestion + "\n")
                    popup.stdin.flush()
                except (BrokenPipeError, ValueError):
                    break  # popup was closed early
            try:
                popup.stdin.write("__DONE__\n")
                popup.stdin.flush()
                popup.stdin.close()
            except (BrokenPipeError, ValueError):
                pass
        except Exception:
            log.exception("Streaming generation failed")
            popup.terminate()
            return

        if count == 0:
            log.warning("No suggestions returned by the model")
            popup.terminate()
            return

        log.info("Streamed %d suggestion(s) to popup", count)
        chosen = popup.stdout.readline().strip()
        log.debug("popup chose: %r", chosen)
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
