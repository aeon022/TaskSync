import asyncio
import os
import signal
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# Template for macOS launchd
LAUNCHD_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aeon022.utaskd</string>
    <key>ProgramArguments</key>
    <array>
{program_args}
        <string>daemon</string>
        <string>--interval</string>
        <string>300</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""

def program_arguments() -> str:
    """ProgramArguments entries for the plist. A PyInstaller binary starts itself (`utask daemon`); a Python install starts
    the interpreter with the entry script. Both values are XML-escaped (paths may contain & or <)."""
    if getattr(sys, "frozen", False):
        items = [sys.executable]
    else:
        items = [sys.executable, os.path.abspath(sys.argv[0])]
    return "\n".join(f"        <string>{escape(i)}</string>" for i in items)

def install_daemon():
    """Installs the utaskd plist into ~/Library/LaunchAgents."""
    program_args = program_arguments()

    log_dir = Path.home() / ".config" / "tasksync"
    log_path = log_dir / "daemon.log"
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.aeon022.utaskd.plist"
    
    content = LAUNCHD_PLIST.format(program_args=program_args, log_path=escape(str(log_path)))
    
    os.makedirs(plist_path.parent, exist_ok=True)
    with open(plist_path, "w") as f:
        f.write(content)
    
    return str(plist_path)

async def daemon_loop(engine, interval: int):
    """Resilient daemon loop with exponential backoff on failure."""
    from .core import logger
    logger.info("Daemon started. Entering sync loop.")
    
    # Handle termination signals gracefully
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: logger.info("Daemon received stop signal."))
        except NotImplementedError: pass # Windows

    backoff = 0
    while True:
        try:
            await engine.sync_all()
            backoff = 0 # Reset on success
            await asyncio.sleep(interval)
        except Exception as e:
            backoff = min(backoff + 60, 1800) # Max 30 min backoff
            logger.error(f"Daemon sync failed: {e}. Retrying in {backoff}s")
            await asyncio.sleep(backoff)
