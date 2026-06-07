import json
import logging
import time
from pathlib import Path

_HISTORY_FILE = Path.home() / ".tinyblabla_history.jsonl"
_MAX_ENTRY_LEN = 120

log = logging.getLogger(__name__)


_KEEP = 3


def save_entry(original: str, chosen: str) -> None:
    entry = {"original": original[:_MAX_ENTRY_LEN], "chosen": chosen[:_MAX_ENTRY_LEN], "ts": time.time()}
    try:
        existing = load_recent(_KEEP - 1)
        lines = [json.dumps(e, ensure_ascii=False) for e in existing]
        lines.append(json.dumps(entry, ensure_ascii=False))
        _HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.debug("History saved (%d entries kept): %r -> %r", len(lines), original[:40], chosen[:40])
    except OSError as e:
        log.warning("Could not write history to %s: %s", _HISTORY_FILE, e)


def load_recent(n: int = 3) -> list:
    if not _HISTORY_FILE.exists():
        log.debug("No history file found at %s", _HISTORY_FILE)
        return []
    try:
        lines = _HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                log.warning("Skipping malformed history line: %r", line[:60])
                continue
            if len(entries) == n:
                break
        result = list(reversed(entries))
        log.debug("Loaded %d history entry/entries from %s", len(result), _HISTORY_FILE)
        return result
    except OSError as e:
        log.warning("Could not read history from %s: %s", _HISTORY_FILE, e)
        return []
