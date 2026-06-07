"""
Instant loading spinner shown the moment the hotkey is pressed, while the
model generates suggestions.

Spawned by the daemon as a subprocess and terminated once suggestions are
ready. Cocoa runs on this process's own main thread, which avoids the
main-thread conflicts the daemon would hit if it drove AppKit itself.
"""
import AppKit


def main():
    app = AppKit.NSApplication.sharedApplication()
    # Accessory: can show windows without a Dock icon or menu bar.
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        AppKit.NSMakeRect(0, 0, 240, 80),
        AppKit.NSWindowStyleMaskBorderless,
        AppKit.NSBackingStoreBuffered,
        False,
    )
    win.setLevel_(AppKit.NSFloatingWindowLevel)
    win.setBackgroundColor_(AppKit.NSColor.windowBackgroundColor())
    win.setOpaque_(True)
    win.center()

    content = win.contentView()

    spinner = AppKit.NSProgressIndicator.alloc().initWithFrame_(
        AppKit.NSMakeRect(20, 24, 32, 32)
    )
    spinner.setStyle_(AppKit.NSProgressIndicatorStyleSpinning)
    spinner.setIndeterminate_(True)
    spinner.startAnimation_(None)
    content.addSubview_(spinner)

    label = AppKit.NSTextField.alloc().initWithFrame_(
        AppKit.NSMakeRect(64, 28, 160, 24)
    )
    label.setStringValue_("Reformulating…")
    label.setBezeled_(False)
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setDrawsBackground_(False)
    label.setFont_(AppKit.NSFont.systemFontOfSize_(14))
    content.addSubview_(label)

    win.orderFrontRegardless()
    app.activateIgnoringOtherApps_(True)
    # Runs until the daemon terminates this process (SIGTERM) once results
    # are ready.
    app.run()


if __name__ == "__main__":
    main()
