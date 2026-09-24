"""
OpenAI (ChatGPT) API-powered reformulation daemon.
Sends the selected text to OpenAI's Chat Completions API and gets back a
complete reformulation in a single request (no local model, no GPU/MPS needed).

Requirements: pip install openai
Auth: export OPENAI_API_KEY=sk-...
"""
import json
import logging
import os
import pathlib
import subprocess
import sys
import time
import threading

import openai
from openai import OpenAI
from pynput import keyboard

from tinyblabla.language import detect_language
from tinyblabla.parser import parse_suggestions

_ROOT = pathlib.Path(__file__).resolve().parent.parent

HOTKEY = "<ctrl>+<shift>+<space>"
MODEL_NAME = "gpt-4o"
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

if not os.environ.get("OPENAI_API_KEY"):
    log.error(
        "No OpenAI credentials found. Set OPENAI_API_KEY before starting this daemon."
    )
    sys.exit(1)

client = OpenAI()
log.info("Using OpenAI API (%s). Hotkey active: Ctrl+Shift+Space", MODEL_NAME)

kb = keyboard.Controller()
_busy = threading.Lock()


def _build_prompt(sentence):
    lang = detect_language(sentence)
    log.debug("Detected language: %s", lang)
    return (
        f"Correct all grammar, syntax, tense, and logic errors in the following {lang} text. "
        "Infer the most likely intended meaning and rewrite it correctly. "
        f"Your response MUST be entirely in {lang}; do not translate. "
        "Output ONLY 5 numbered reformulations (1. through 5.), each on its "
        "own single line. Do not add any preamble, explanation, or commentary.\n\n"
        f"Text:\n{sentence}"
    )


def reformulate(sentence, max_tokens=600):
    log.debug("Reformulating: %r", sentence)
    prompt = _build_prompt(sentence)
    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except openai.AuthenticationError:
        log.error("OpenAI authentication failed — check OPENAI_API_KEY")
        return []
    except openai.RateLimitError as e:
        log.error("Rate limited by OpenAI API: %s", e)
        return []
    except openai.APIStatusError as e:
        log.error("OpenAI API error (%s): %s", e.status_code, e.message)
        return []
    except openai.APIConnectionError:
        log.error("Could not reach the OpenAI API — check your internet connection")
        return []

    choice = response.choices[0]
    if choice.finish_reason == "content_filter":
        log.warning("OpenAI declined the request (finish_reason=content_filter)")
        return []

    raw = (choice.message.content or "").strip()
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
        # API request is in flight (network round trip takes a couple seconds).
        loader = subprocess.Popen(
            [sys.executable, str(_ROOT / "ui" / "loader_worker.py")],
            cwd=str(_ROOT),
        )
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
            [sys.executable, str(_ROOT / "ui" / "popup_worker.py"), json.dumps(suggestions)],
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
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
