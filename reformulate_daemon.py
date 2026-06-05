import json
import logging
import subprocess
import sys
import time
import threading
import torch
from pynput import keyboard
from transformers import AutoModelForCausalLM, AutoTokenizer

HOTKEY = "<ctrl>+<shift>+<space>"
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
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

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

log.info("Loading Mistral 7B model... (device: %s)", DEVICE)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=torch.float16, low_cpu_mem_usage=True)
model = model.to(DEVICE)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token
model.eval()
try:
    model = torch.compile(model, mode="reduce-overhead")
    log.info("torch.compile() applied")
except Exception as e:
    log.warning("torch.compile() skipped: %s", e)

log.info("Warming up model (first inference is slow)...")
with torch.inference_mode():
    _w = tokenizer("warm up", return_tensors="pt").to(DEVICE)
    model.generate(**_w, max_new_tokens=5, pad_token_id=tokenizer.eos_token_id)
log.info("Warmup done. Hotkey active: Ctrl+Shift+Space")

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


@torch.inference_mode()
def reformulate(sentence, max_new_tokens=300):
    log.debug("Reformulating: %r", sentence)
    lang = detect_language(sentence)
    log.debug("Detected language: %s", lang)
    messages = [{
        "role": "user",
        "content": (
            f"Rewrite the following {lang} sentence with better grammar and style. "
            f"Your response MUST be entirely in {lang}, do not translate. "
            "Output exactly 5 numbered reformulations, nothing else.\n"
            f"Sentence: {sentence}"
        ),
    }]
    inputs = tokenizer.apply_chat_template(messages, return_tensors="pt", return_dict=True)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    outputs = model.generate(
        **inputs, max_new_tokens=max_new_tokens, temperature=0.7, do_sample=True, top_p=0.9,
        pad_token_id=tokenizer.eos_token_id,
    )
    input_len = inputs["input_ids"].shape[1]
    raw = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
    log.debug("Raw model output: %r", raw)
    suggestions = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading numbering "1. " or "1) "
        if len(line) > 2 and line[0].isdigit() and line[1] in ".)" and line[2:3] == " ":
            suggestions.append(line[3:].strip())
        elif len(line) > 3 and line[:2].isdigit() and line[2] in ".)" and line[3:4] == " ":
            suggestions.append(line[4:].strip())
        else:
            suggestions.append(line)
    result = [s for s in suggestions if s]
    log.info("%d suggestion(s) generated", len(result))
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

def select_sentence():
    with kb.pressed(keyboard.Key.cmd):
        with kb.pressed(keyboard.Key.shift):
            kb.press(keyboard.Key.left)
            kb.release(keyboard.Key.left)
    time.sleep(0.08)

def grab_sentence():
    log.debug("Selecting and copying current sentence")
    select_sentence()
    with kb.pressed(keyboard.Key.cmd):
        kb.press("c")
        kb.release("c")
    time.sleep(0.08)
    return clipboard_read().strip()


def handle_hotkey():
    if not _busy.acquire(blocking=False):
        log.warning("Already processing, hotkey ignored")
        return
    try:
        log.info("Hotkey triggered — grabbing sentence")
        source_app = get_frontmost_app()
        log.debug("Source app: %s", source_app)

        sentence = grab_sentence()
        log.debug("Sentence grabbed: %r", sentence)

        suggestions = reformulate(sentence)
        if not suggestions:
            log.warning("No suggestions returned by the model")
            return

        log.info("Opening popup with %d suggestion(s)", len(suggestions))
        result = subprocess.run(
            [sys.executable, "popup_worker.py", json.dumps(suggestions)],
            capture_output=True,
            text=True,
            cwd=__file__[:__file__.rfind("/")],
        )
        if result.stderr.strip():
            log.error("popup_worker stderr:\n%s", result.stderr.strip())
        log.debug("popup_worker returncode: %d", result.returncode)
        chosen = result.stdout.strip()
        if chosen:
            activate_app(source_app)
            select_sentence()
            paste_text(chosen)
        else:
            log.info("Popup closed without selection")
    except Exception:
        log.exception("Unexpected error in handle_hotkey")
    finally:
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
