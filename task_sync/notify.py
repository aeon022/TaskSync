"""macOS notifications without building AppleScript from user data (task titles come from remote lists)."""
import subprocess

_SCRIPT = ["on run argv", "display notification (item 1 of argv) with title (item 2 of argv)", "end run"]

def notify_args(message: str, title: str = "utask") -> list:
    """osascript command line: the text travels as arguments, never as part of the script."""
    cmd = ["osascript"]
    for line in _SCRIPT:
        cmd += ["-e", line]
    return cmd + ["--", message, title]

def notify(message: str, title: str = "utask") -> None:
    try:
        subprocess.run(notify_args(message, title), capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass  # a missing notification must never break the app
