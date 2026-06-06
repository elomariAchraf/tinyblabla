"""
Standalone popup process. Receives suggestions as JSON via argv[1].
Prints the chosen suggestion to stdout and exits.
Uses osascript (AppleScript) to avoid tkinter/Tcl-Tk macOS version issues.
"""
import json
import sys
import subprocess


def _as_string(s):
    # AppleScript has no backslash escaping; split on " and rejoin via & quote &
    parts = s.split('"')
    return ' & quote & '.join(f'"{part}"' for part in parts)


def main():
    suggestions = json.loads(sys.argv[1])
    items = ', '.join(_as_string(s) for s in suggestions)
    script = f"""\
set choices to {{{items}}}
set chosen to choose from list choices with title "Reformulations" with prompt "Choose a reformulation:" without multiple selections allowed
if chosen is false then
    return ""
end if
return item 1 of chosen
"""
    result = subprocess.run(["osascript"], input=script, capture_output=True, text=True)
    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            print(output)


if __name__ == "__main__":
    main()
