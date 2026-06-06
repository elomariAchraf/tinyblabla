"""
Streaming reformulation popup (used by the MLX daemon).

A native AppKit window that appears instantly with a spinner and fills in with
suggestions as they stream in over stdin — one suggestion per line, terminated
by a "__DONE__" sentinel. The chosen suggestion is printed to stdout.

Runs as a subprocess so Cocoa owns its own main thread (the daemon can't drive
AppKit from a worker thread). Selection: arrow keys + Return, number keys 1-9,
double-click; Esc or closing the window cancels (empty stdout).
"""
import os
import sys
import threading
import queue

import objc
from Foundation import NSObject, NSIndexSet, NSTimer, NSMakeRect
from AppKit import (
    NSApplication,
    NSWindow,
    NSScrollView,
    NSTableView,
    NSTableColumn,
    NSProgressIndicator,
    NSTextField,
    NSButton,
    NSFont,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskResizable,
    NSBackingStoreBuffered,
    NSProgressIndicatorStyleSpinning,
    NSApplicationActivationPolicyRegular,
    NSBezelStyleRounded,
    NSEvent,
    NSScreen,
)

DONE = "__DONE__"
NSBezelBorder = 2

_q = queue.Queue()
_suggestions = []
TABLE = None
SPINNER = None
LABEL = None


def _emit_and_exit(text):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    os._exit(0)


def _confirm():
    row = TABLE.selectedRow()
    if 0 <= row < len(_suggestions):
        _emit_and_exit(_suggestions[row])


class TableView(NSTableView):
    def keyDown_(self, event):
        code = event.keyCode()
        chars = event.charactersIgnoringModifiers() or ""
        if code == 53:            # Esc
            os._exit(0)
        if code in (36, 76):      # Return / keypad Enter
            _confirm()
            return
        if chars in "123456789":
            idx = int(chars) - 1
            if 0 <= idx < len(_suggestions):
                TABLE.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(idx), False
                )
                _confirm()
                return
        objc.super(TableView, self).keyDown_(event)


class Helper(NSObject):
    # Drains the stdin queue on the main thread and updates the UI.
    def tick_(self, timer):
        changed = False
        try:
            while True:
                item = _q.get_nowait()
                if item == DONE:
                    if SPINNER is not None:
                        SPINNER.stopAnimation_(None)
                        SPINNER.setHidden_(True)
                    n = len(_suggestions)
                    if n:
                        LABEL.setStringValue_(
                            "Choose a reformulation   (1-%d, ↑/↓, Return, Esc)" % n
                        )
                    else:
                        LABEL.setStringValue_("No suggestions   (Esc to close)")
                elif len(_suggestions) < 9:
                    _suggestions.append(item)
                    changed = True
        except queue.Empty:
            pass
        if changed:
            TABLE.reloadData()
            if TABLE.selectedRow() < 0:
                TABLE.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(0), False
                )

    # NSTableView data source
    def numberOfRowsInTableView_(self, tv):
        return len(_suggestions)

    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        return "%d.  %s" % (row + 1, _suggestions[row])

    def doubleClick_(self, sender):
        _confirm()

    def okClicked_(self, sender):
        _confirm()

    def cancelClicked_(self, sender):
        os._exit(0)


def _stdin_reader():
    for line in sys.stdin:
        line = line.rstrip("\n")
        if line:
            _q.put(line)
    _q.put(DONE)


def _position_away_from_cursor(win):
    """Place the window in the opposite vertical half of the screen from the
    mouse cursor (which is at the text the user just selected), so the popup
    doesn't cover the selection."""
    mouse = NSEvent.mouseLocation()
    screen = None
    for s in NSScreen.screens():
        f = s.frame()
        if (f.origin.x <= mouse.x <= f.origin.x + f.size.width
                and f.origin.y <= mouse.y <= f.origin.y + f.size.height):
            screen = s
            break
    if screen is None:
        screen = NSScreen.mainScreen()
    vis = screen.visibleFrame()
    fw = win.frame().size.width
    fh = win.frame().size.height
    margin = 40.0
    x = vis.origin.x + (vis.size.width - fw) / 2.0
    mid = vis.origin.y + vis.size.height / 2.0
    if mouse.y >= mid:
        y = vis.origin.y + margin                          # cursor high -> popup low
    else:
        y = vis.origin.y + vis.size.height - fh - margin   # cursor low -> popup high
    win.setFrameOrigin_((x, y))


def main():
    global TABLE, SPINNER, LABEL
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, 560, 384),
        NSWindowStyleMaskTitled | NSWindowStyleMaskResizable,
        NSBackingStoreBuffered,
        False,
    )
    win.setTitle_("Reformulations")
    _position_away_from_cursor(win)
    content = win.contentView()

    SPINNER = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(16, 350, 18, 18))
    SPINNER.setStyle_(NSProgressIndicatorStyleSpinning)
    SPINNER.setIndeterminate_(True)
    SPINNER.startAnimation_(None)
    content.addSubview_(SPINNER)

    LABEL = NSTextField.alloc().initWithFrame_(NSMakeRect(42, 348, 500, 20))
    LABEL.setStringValue_("Reformulating…")
    LABEL.setBezeled_(False)
    LABEL.setEditable_(False)
    LABEL.setDrawsBackground_(False)
    LABEL.setFont_(NSFont.systemFontOfSize_(13))
    content.addSubview_(LABEL)

    helper = Helper.alloc().init()

    scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(16, 56, 528, 284))
    scroll.setHasVerticalScroller_(True)
    scroll.setBorderType_(NSBezelBorder)

    TABLE = TableView.alloc().initWithFrame_(NSMakeRect(0, 0, 526, 284))
    col = NSTableColumn.alloc().initWithIdentifier_("s")
    col.setWidth_(508)
    TABLE.addTableColumn_(col)
    TABLE.setHeaderView_(None)
    TABLE.setDataSource_(helper)
    TABLE.setTarget_(helper)
    TABLE.setDoubleAction_("doubleClick:")
    TABLE.setRowHeight_(24)
    scroll.setDocumentView_(TABLE)
    content.addSubview_(scroll)

    # Mouse-friendly buttons (Return triggers OK, Esc triggers Cancel).
    cancel = NSButton.alloc().initWithFrame_(NSMakeRect(364, 12, 86, 32))
    cancel.setTitle_("Cancel")
    cancel.setBezelStyle_(NSBezelStyleRounded)
    cancel.setTarget_(helper)
    cancel.setAction_("cancelClicked:")
    cancel.setKeyEquivalent_("\x1b")  # Esc
    content.addSubview_(cancel)

    ok = NSButton.alloc().initWithFrame_(NSMakeRect(458, 12, 86, 32))
    ok.setTitle_("OK")
    ok.setBezelStyle_(NSBezelStyleRounded)
    ok.setTarget_(helper)
    ok.setAction_("okClicked:")
    ok.setKeyEquivalent_("\r")  # Return = default button
    content.addSubview_(ok)

    threading.Thread(target=_stdin_reader, daemon=True).start()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.05, helper, "tick:", None, True
    )

    win.makeKeyAndOrderFront_(None)
    win.makeFirstResponder_(TABLE)
    app.activateIgnoringOtherApps_(True)
    app.run()


if __name__ == "__main__":
    main()
