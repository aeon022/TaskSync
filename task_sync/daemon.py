import asyncio
import os
import signal
import sys
from pathlib import Path

# Template for macOS launchd
LAUNCHD_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aeon022.utaskd</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{main_path}</string>
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

def install_daemon():
    """Installs the utaskd plist into ~/Library/LaunchAgents."""
    python_path = sys.executable
    main_path = os.path.abspath(sys.argv[0])
    # If running via wrapper, we need the actual entry point
    if main_path.endswith("utask") and not main_path.endswith(".py"):
        # Assume it's the wrapper or installed script
        pass 
    
    log_dir = Path.home() / ".config" / "tasksync"
    log_path = log_dir / "daemon.log"
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.aeon022.utaskd.plist"
    
    content = LAUNCHD_PLIST.format(
        python_path=python_path,
        main_path=main_path,
        log_path=log_path
    )
    
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
