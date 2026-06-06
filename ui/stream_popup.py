"""
Streaming reformulation popup — bubble style.

A borderless dark bubble that appears near the cursor, shows a spinner while
the model generates, then fills with suggestions as they stream in one by one.
Chosen suggestion is printed to stdout; Esc / closing prints nothing.
"""
import os
import sys
import threading
import queue

import objc
from Foundation import (
    NSObject, NSIndexSet, NSTimer, NSMakeRect,
    NSAttributedString,
)
from AppKit import (
    NSApplication,
    NSWindow,
    NSScrollView,
    NSTableView,
    NSTableColumn,
    NSProgressIndicator,
    NSTextField,
    NSColor,
    NSFont,
    NSBezierPath,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSProgressIndicatorStyleSpinning,
    NSApplicationActivationPolicyRegular,
    NSForegroundColorAttributeName,
    NSFontAttributeName,
    NSEvent,
    NSScreen,
    NSFloatingWindowLevel,
    NSView,
)

DONE = "__DONE__"

_q = queue.Queue()
_suggestions = []
TABLE = None
SPINNER = None
LABEL = None
APP = None
WIN = None
_activated = False
_header_collapsed = False

W_MIN = 300
W_MAX = 680
W_PAD = 56       # horizontal padding added around the longest suggestion text
_current_w = W_MIN
HEADER_H = 48
ROW_H = 38
FOOTER_H = 8
MAX_ROWS = 5

# colours
BG        = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.11, 0.11, 0.14, 0.96)
TEXT      = NSColor.colorWithCalibratedWhite_alpha_(0.93, 1.0)
SUBTEXT   = NSColor.colorWithCalibratedWhite_alpha_(0.50, 1.0)
FONT_MAIN = NSFont.systemFontOfSize_(13.5)
FONT_SUB  = NSFont.systemFontOfSize_(12.0)


def _optimal_width():
    """Return the ideal window width clamped to [W_MIN, W_MAX]."""
    if not _suggestions:
        return W_MIN
    max_px = 0.0
    for i, s in enumerate(_suggestions):
        label = "%d.  %s" % (i + 1, s)
        w = (NSAttributedString.alloc()
             .initWithString_attributes_(label, {NSFontAttributeName: FONT_MAIN})
             .size().width)
        if w > max_px:
            max_px = w
    return max(W_MIN, min(W_MAX, int(max_px) + W_PAD))


def _bubble_height(n_rows):
    header = 0 if _header_collapsed else HEADER_H
    return header + n_rows * ROW_H + FOOTER_H


def _emit_and_exit(text):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    os._exit(0)


def _confirm():
    row = TABLE.selectedRow()
    if 0 <= row < len(_suggestions):
        _emit_and_exit(_suggestions[row])


# ── Custom views ──────────────────────────────────────────────────────────────

class BubbleView(NSView):
    def drawRect_(self, rect):
        BG.setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, 14.0, 14.0).fill()

    def isOpaque(self):
        return False


class BubbleWindow(NSWindow):
    """Borderless window that accepts keyboard focus."""
    def canBecomeKeyWindow(self):
        return True

    def cancelOperation_(self, sender):
        os._exit(0)

    def resignKeyWindow(self):
        objc.super(BubbleWindow, self).resignKeyWindow()
        if _activated:
            os._exit(0)


class SuggestionTableView(NSTableView):
    def keyDown_(self, event):
        code = event.keyCode()
        chars = event.charactersIgnoringModifiers() or ""
        if code == 53:          # Esc
            os._exit(0)
        if code in (36, 76):    # Return / numpad Enter
            _confirm()
            return
        if code == 48:          # Tab — move down, wrap around
            n = len(_suggestions)
            if n:
                cur = TABLE.selectedRow()
                nxt = (cur + 1) % n
                TABLE.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(nxt), False
                )
                TABLE.scrollRowToVisible_(nxt)
            return
        if chars in "123456789":
            idx = int(chars) - 1
            if 0 <= idx < len(_suggestions):
                TABLE.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(idx), False
                )
                _confirm()
                return
        objc.super(SuggestionTableView, self).keyDown_(event)


# ── Helper (data source + delegate + timer) ───────────────────────────────────

class Helper(NSObject):

    def tick_(self, timer):
        global _activated
        changed = False
        done = False
        try:
            while True:
                item = _q.get_nowait()
                if item == DONE:
                    done = True
                    SPINNER.stopAnimation_(None)
                    SPINNER.setHidden_(True)
                    LABEL.setHidden_(True)
                    pass  # hint removed
                elif len(_suggestions) < MAX_ROWS:
                    _suggestions.append(item)
                    changed = True
        except queue.Empty:
            pass

        if changed:
            if not _header_collapsed:
                _collapse_header()
            _grow_to(len(_suggestions))
            TABLE.reloadData()
            if TABLE.selectedRow() < 0:
                TABLE.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(0), False
                )

        if not _activated and (_suggestions or done):
            _activated = True
            APP.activateIgnoringOtherApps_(True)
            WIN.makeKeyAndOrderFront_(None)
            WIN.makeFirstResponder_(TABLE)

    # ── NSTableViewDataSource ──────────────────────────────────────────────

    def numberOfRowsInTableView_(self, tv):
        return len(_suggestions)

    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        text = "%d.  %s" % (row + 1, _suggestions[row])
        attrs = {
            NSForegroundColorAttributeName: TEXT,
            NSFontAttributeName: FONT_MAIN,
        }
        return NSAttributedString.alloc().initWithString_attributes_(text, attrs)

    def doubleClick_(self, sender):
        _confirm()


# ── Layout helpers ────────────────────────────────────────────────────────────

def _collapse_header():
    global _header_collapsed
    _header_collapsed = True
    SPINNER.stopAnimation_(None)
    SPINNER.setHidden_(True)
    LABEL.setHidden_(True)
    # Remove the header band instantly (keep bottom edge fixed)
    cur = WIN.frame()
    new_h = cur.size.height - HEADER_H
    WIN.setFrame_display_animate_(
        NSMakeRect(cur.origin.x, cur.origin.y, _current_w, new_h), True, False
    )


def _grow_to(n_rows):
    global _current_w
    new_w = _optimal_width()
    new_h = _bubble_height(n_rows)
    cur = WIN.frame()
    w_changed = new_w != _current_w
    h_changed = new_h != cur.size.height
    if not w_changed and not h_changed:
        return
    delta_h = new_h - cur.size.height
    # Keep top edge fixed: lower origin as height grows; shift left if width grows
    new_frame = NSMakeRect(cur.origin.x, cur.origin.y - delta_h, new_w, new_h)
    WIN.setFrame_display_animate_(new_frame, True, True)
    if not _header_collapsed:
        _layout_header(new_h)
    if w_changed:
        _current_w = new_w
        LABEL.setFrameSize_((new_w - 54, 20))
        TABLE.tableColumns()[0].setWidth_(new_w - 4)
    table_h = n_rows * ROW_H
    TABLE.enclosingScrollView().setFrame_(NSMakeRect(0, FOOTER_H, new_w, table_h))
    TABLE.setFrameSize_((new_w, table_h))


def _layout_header(h):
    SPINNER.setFrameOrigin_((14, h - HEADER_H + (HEADER_H - 18) // 2))
    LABEL.setFrameOrigin_((40, h - HEADER_H + (HEADER_H - 20) // 2))


def _position_near_cursor(win):
    mouse = NSEvent.mouseLocation()
    screen = NSScreen.mainScreen()
    for s in NSScreen.screens():
        f = s.frame()
        if (f.origin.x <= mouse.x <= f.origin.x + f.size.width
                and f.origin.y <= mouse.y <= f.origin.y + f.size.height):
            screen = s
            break
    vis = screen.visibleFrame()
    fh = win.frame().size.height
    GAP = 18
    x = mouse.x + GAP
    y = mouse.y - fh - GAP
    if x + _current_w > vis.origin.x + vis.size.width:
        x = mouse.x - _current_w - GAP
    if y < vis.origin.y:
        y = mouse.y + GAP
    win.setFrameOrigin_((x, y))


# ── Stdin reader ──────────────────────────────────────────────────────────────

def _stdin_reader():
    for line in sys.stdin:
        line = line.rstrip("\n")
        if line:
            _q.put(line)
    _q.put(DONE)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global TABLE, SPINNER, LABEL, APP, WIN

    app = NSApplication.sharedApplication()
    APP = app
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    init_h = _bubble_height(0)

    win = BubbleWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, W_MIN, init_h),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    win.setBackgroundColor_(NSColor.clearColor())
    win.setOpaque_(False)
    win.setHasShadow_(True)
    win.setLevel_(NSFloatingWindowLevel)
    WIN = win

    bubble = BubbleView.alloc().initWithFrame_(NSMakeRect(0, 0, W_MIN, init_h))
    win.setContentView_(bubble)
    content = bubble

    SPINNER = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(14, 0, 18, 18))
    SPINNER.setStyle_(NSProgressIndicatorStyleSpinning)
    SPINNER.setControlSize_(1)
    SPINNER.setIndeterminate_(True)
    SPINNER.startAnimation_(None)
    content.addSubview_(SPINNER)

    LABEL = NSTextField.alloc().initWithFrame_(NSMakeRect(40, 0, W_MIN - 54, 20))
    LABEL.setStringValue_("Reformulating…")
    LABEL.setBezeled_(False)
    LABEL.setEditable_(False)
    LABEL.setSelectable_(False)
    LABEL.setDrawsBackground_(False)
    LABEL.setTextColor_(SUBTEXT)
    LABEL.setFont_(FONT_SUB)
    content.addSubview_(LABEL)

    _layout_header(init_h)

    helper = Helper.alloc().init()

    scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, FOOTER_H, W_MIN, 0))
    scroll.setHasVerticalScroller_(False)
    scroll.setBorderType_(0)
    scroll.setDrawsBackground_(False)

    TABLE = SuggestionTableView.alloc().initWithFrame_(NSMakeRect(0, 0, W_MIN, 0))
    col = NSTableColumn.alloc().initWithIdentifier_("s")
    col.setWidth_(W_MIN - 4)
    TABLE.addTableColumn_(col)
    TABLE.setHeaderView_(None)
    TABLE.setDataSource_(helper)
    TABLE.setDelegate_(helper)
    TABLE.setTarget_(helper)
    TABLE.setDoubleAction_("doubleClick:")
    TABLE.setRowHeight_(ROW_H)
    TABLE.setBackgroundColor_(NSColor.clearColor())
    TABLE.setGridStyleMask_(0)
    scroll.setDocumentView_(TABLE)
    content.addSubview_(scroll)

    _position_near_cursor(win)

    threading.Thread(target=_stdin_reader, daemon=True).start()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.05, helper, "tick:", None, True
    )

    win.orderFrontRegardless()
    app.run()


if __name__ == "__main__":
    main()
