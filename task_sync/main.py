import typer
import asyncio
import sys
from typing import Optional

app = typer.Typer(help="utask v2.0 - Headless Task Sync CLI")

def get_engine():
    from .core import SyncEngine
    from .providers.apple import AppleRemindersProvider
    from .providers.google import GoogleTasksProvider
    from .providers.microsoft import MicrosoftToDoProvider
    
    # In a real multi-account setup, we would load these from a config
    # For now, we set the labels to distinguish them
    apple = AppleRemindersProvider()
    google = GoogleTasksProvider()
    ms_fh = MicrosoftToDoProvider()
    ms_fh.account_label = "FH" # Override default MS label
    
    providers = [apple, google, ms_fh]
    return SyncEngine(providers=providers)

@app.command()
def sync():
    """Run a one-time full sync."""
    from .core import init_db
    engine = get_engine()
    
    async def run():
        await init_db()
        await engine.sync_all()
    
    asyncio.run(run())
    typer.echo("Sync complete.")

@app.command()
def daemon(interval: int = 300):
    """Start the utaskd sync daemon (active process)."""
    from .core import init_db
    from .daemon import daemon_loop
    engine = get_engine()
    
    async def run():
        await init_db()
        await daemon_loop(engine, interval)
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        typer.echo("Daemon stopped.")

@app.command()
def daemon_start():
    """Install and start the background daemon as a macOS service."""
    from .daemon import install_daemon
    import subprocess
    
    plist_path = install_daemon()
    try:
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        subprocess.run(["launchctl", "load", plist_path], check=True)
        typer.echo(f"✅ Daemon installed and started: {plist_path}")
    except Exception as e:
        typer.echo(f"❌ Failed to start daemon: {e}")

@app.command()
def daemon_stop():
    """Stop and uninstall the background daemon."""
    import os
    from pathlib import Path
    import subprocess
    
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.aeon022.utaskd.plist"
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        os.remove(plist_path)
        typer.echo("✅ Daemon stopped and service removed.")
    else:
        typer.echo("⚠️ No daemon service found.")

@app.command()
def ui():
    """Launch the TUI."""
    from .tui import UniversalTaskApp
    UniversalTaskApp().run()

@app.command(name="list")
def list_tasks():
    """List local tasks from SQLite."""
    from .core import AsyncSessionLocal
    from .models import Task
    from sqlmodel import select
    
    async def run():
        async with AsyncSessionLocal() as session:
            statement = select(Task)
            result = await session.execute(statement)
            tasks = result.scalars().all()
            for t in tasks:
                status = "✅" if t.status == "completed" else "◯"
                typer.echo(f"{status} {t.title} ({t.list_name})")
    
    asyncio.run(run())

@app.command()
def add(title: str, list_name: str = "Apple"):
    """Add a new task with NLP date parsing (e.g. 'Meeting morgen 15:00')."""
    from .core import AsyncSessionLocal, init_db, TaskList
    from .models import Task
    import dateparser
    from datetime import datetime, timezone
    from sqlmodel import select

    # NLP: Extract date using dateparser
    # We use a base date of now and prefer future dates
    parsed_date = dateparser.parse(
        title, 
        settings={'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    
    # If a date was found, we might want to strip it from the title for a cleaner look
    # For now, we keep it simple and just use the parsed date as due_date
    
    async def run():
        await init_db()
        async with AsyncSessionLocal() as session:
            # Check if list exists, prepend default provider if not specified
            # For simplicity, we use the display name format "[Apple] Reminders"
            # If the user just types "Reminders", we try to find it
            stmt = select(TaskList).where(TaskList.name.contains(list_name))
            result = await session.execute(stmt)
            found_list = result.scalars().first()
            
            effective_list = found_list.name if found_list else f"[Apple] {list_name}"
            
            new_task = Task(
                title=title, 
                list_name=effective_list,
                due_date=parsed_date,
                last_modified=datetime.now(timezone.utc)
            )
            session.add(new_task)
            await session.commit()
            
            typer.echo(f"✅ Added: '{title}' to {effective_list}")
            if parsed_date:
                typer.echo(f"📅 Due: {parsed_date.strftime('%Y-%m-%d %H:%M')}")
    
    asyncio.run(run())

@app.command()
def export(format: str = "md"):
    """Export all tasks to a file (default: markdown)."""
    from .core import AsyncSessionLocal
    from .models import Task
    from sqlmodel import select
    from pathlib import Path
    
    async def run():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Task))
            tasks = result.scalars().all()
            
            if format == "md":
                output_path = Path.cwd() / "utask_export.md"
                with open(output_path, "w") as f:
                    f.write("# utask Export\n\n")
                    # Group by list
                    lists = sorted(set(t.list_name for t in tasks))
                    for l_name in lists:
                        f.write(f"## {l_name}\n")
                        list_tasks = [t for t in tasks if t.list_name == l_name]
                        for t in list_tasks:
                            status = "x" if t.status == "completed" else " "
                            f.write(f"- [{status}] {t.title}\n")
                        f.write("\n")
                typer.echo(f"🚀 Exported to {output_path}")

    asyncio.run(run())

@app.command()
def auth_google(
    client_id: Optional[str] = typer.Option(None, help="Google Client ID"),
    client_secret: Optional[str] = typer.Option(None, help="Google Client Secret")
):
    """Start Google Tasks authorization flow (Paste JSON OR provide --client-id and --client-secret)."""
    from .auth import auth_google as perform_auth
    from .auth import auth_google_manual
    
    try:
        if client_id and client_secret:
            msg = auth_google_manual(client_id, client_secret)
        else:
            typer.echo("Bitte kopiere den INHALT der Google JSON-Datei (beginnend mit { ) hier hinein.")
            typer.echo("Drücke danach STRG+D zum Speichern.")
            json_data = sys.stdin.read().strip()
            if not json_data:
                typer.echo("Abbruch: Keine Daten empfangen.")
                return
            msg = perform_auth(json_data)
        
        typer.echo(f"✅ {msg}")
    except Exception as e:
        typer.echo(f"❌ Fehler: {e}")
        typer.echo("\nPro-Tipp: Wenn du keine JSON-Datei hast, nutze:")
        typer.echo("utask auth-google --client-id 'ID' --client-secret 'SECRET'")

@app.command()
def auth_microsoft(client_id: str, tenant_id: str = "common"):
    """Save Microsoft App Registration ID."""
    from .auth import auth_microsoft as perform_auth
    msg = perform_auth(client_id, tenant_id)
    typer.echo(f"✅ {msg}")

@app.command()
def logs(lines: int = 20):
    """Display the last N lines of the daemon log."""
    from .core import LOG_FILE
    if not LOG_FILE.exists():
        typer.echo("No log file found.")
        return
    
    with open(LOG_FILE, "r") as f:
        content = f.readlines()
        for line in content[-lines:]:
            typer.echo(line.strip())

if __name__ == "__main__":
    app()
