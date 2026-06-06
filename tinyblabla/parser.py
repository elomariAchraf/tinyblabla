"""Utilities for extracting numbered reformulation suggestions from raw model output."""
import re

# Matches a full numbered line: "1. text" or "2) text"
_NUM_RE = re.compile(r"^\s*(\d{1,2})[.)]\s+(.*)$")

# Matches only the numbered prefix at the start of a line (used in streaming)
_NUM_START = re.compile(r"(?m)^\s*\d{1,2}[.)]\s")


def parse_suggestions(raw: str) -> list:
    """Parse a numbered list from batch model output into a list of strings.

    Joins soft-wrapped continuation lines, stops each item at a blank line,
    and caps the result at 5.
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
                suggestions.append(current.strip())
                current = None
            else:
                current += " " + line.strip()
    if current is not None:
        suggestions.append(current.strip())
    return [s for s in suggestions if s][:5]


def clean_segment(seg: str) -> str:
    """Strip the leading number from one numbered segment and collapse it to a
    single line, stopping at the first blank line (which marks end of item).

    Used by the streaming parser where each segment is the text between two
    numbered prefixes.
    """
    seg = _NUM_START.sub("", seg, count=1)
    out = []
    for ln in seg.splitlines():
        if ln.strip() == "":
            break
        out.append(ln.strip())
    return " ".join(out).strip()


def stream_parse(chunks):
    """Parse a numbered list from an iterable of text chunks (e.g. stream_generate).

    Yields each completed suggestion as soon as the next numbered item begins,
    so the first result surfaces early rather than after all 5 are generated.
    Caps at 5 suggestions.
    """
    buf = ""
    yielded = 0
    for chunk in chunks:
        buf += chunk
        starts = [m.start() for m in _NUM_START.finditer(buf)]
        while yielded + 1 < len(starts) and yielded < 5:
            text = clean_segment(buf[starts[yielded]:starts[yielded + 1]])
            if text:
                yield text
            yielded += 1
        if yielded >= 5:
            return
    # Flush the final in-progress item once the stream ends.
    if yielded < 5:
        starts = [m.start() for m in _NUM_START.finditer(buf)]
        if yielded < len(starts):
            text = clean_segment(buf[starts[yielded]:])
            if text:
                yield text
