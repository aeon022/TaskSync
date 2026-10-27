"""Regression tests for the findings of the 2026-10-27 audit. Run: .venv/bin/python tests/test_security.py"""
import os, subprocess, sys, tempfile
from textual.content import Content
from task_sync.models import Task
from task_sync.notify import notify_args, notify
from task_sync import daemon
from task_sync.tui import TaskItem

BAD_TITLES = ["Buy [/oops] milk", "[bold red]LOUD[/]", "[link=https://evil.example]click me[/link]", "[@click=app.quit]gift[/]",
              "Unclosed [bold title", "[WIP] fix the build", "Notes [2026]", 'x" & (do shell script "id") & "']

# 1. task titles with brackets must render as text (they crashed the interface before)
for t in BAD_TITLES:
    item = TaskItem(Task(id=1, title=t, list_name="l", status="needsAction"))
    plain = Content.from_markup(item._get_content()).plain   # raises MarkupError if the title is parsed as markup
    assert t in plain, (t, plain)                              # and the title is shown as typed

# 2. the notification text is an argument, not part of the AppleScript
evil = 'x" & (do shell script "echo INJECTED > POC") & "'
cmd = notify_args(evil, "utask")
assert evil not in " ".join(cmd[:-3]) and cmd[-3:] == ["--", evil, "utask"], cmd
if sys.platform == "darwin":
    poc = os.path.join(tempfile.mkdtemp(), "poc")
    notify(evil.replace("POC", poc))
    assert not os.path.exists(poc), "AppleScript injection still works"

# 3. launchd entries: escaped, and a frozen binary does not get its own path twice
orig = (sys.executable, sys.argv[0], getattr(sys, "frozen", None))
try:
    sys.executable, sys.argv[0] = "/Applications/A & B/utask", "/Applications/A & B/utask"
    sys.frozen = True
    out = daemon.program_arguments()
    assert out.count("<string>") == 1 and "A &amp; B" in out and "&amp;" in out, out
    sys.frozen = False
    out = daemon.program_arguments()
    assert out.count("<string>") == 2, out
finally:
    sys.executable, sys.argv[0] = orig[0], orig[1]
    if orig[2] is None:
        del sys.frozen
    else:
        sys.frozen = orig[2]
print("ok")
