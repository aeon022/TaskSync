import typer
import asyncio
import sys
from typing import Optional
from pathlib import Path

app = typer.Typer(help="utask v2.0 - Headless Task Sync CLI")
config_app = typer.Typer(help="Manage utask configuration")
app.add_typer(config_app, name="config")

def get_engine():
    from .core import SyncEngine
    from .config import load_provider_config
    from .providers import get_provider
    
    config_providers = load_provider_config()
    providers = []
    
    if not config_providers:
        # Fallback to default Apple provider if no config exists
        apple = get_provider("apple", "Apple")
        if apple:
            providers.append(apple)
    else:
        for p_cfg in config_providers:
            p_instance = get_provider(p_cfg["type"], p_cfg["label"])
            if p_instance:
                providers.append(p_instance)
    
    return SyncEngine(providers=providers)

@config_app.command(name="set-shared")
def config_set_shared(path: str):
    """Set the directory for shared configuration (e.g. iCloud Drive)."""
    from .config import set_shared_dir
    try:
        set_shared_dir(path)
        typer.echo(f"✅ Shared directory set to: {path}")
    except Exception as e:
        typer.echo(f"❌ Error setting shared directory: {e}")

@config_app.command(name="show")
def config_show():
    """Show current configuration paths."""
    from .config import CONFIG_DIR, get_shared_dir, get_providers_file
    typer.echo(f"Local Config:  {CONFIG_DIR}")
    typer.echo(f"Shared Dir:    {get_shared_dir()}")
    typer.echo(f"Providers File: {get_providers_file()}")

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

    parsed_date = dateparser.parse(
        title, 
        settings={'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    
    async def run():
        await init_db()
        async with AsyncSessionLocal() as session:
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
def auth_google(
    client_id: Optional[str] = typer.Option(None, help="Google Client ID"),
    client_secret: Optional[str] = typer.Option(None, help="Google Client Secret"),
    label: str = typer.Option("Google", help="Account label (e.g. Privat, Work)")
):
    """Start Google Tasks authorization flow."""
    from .auth import auth_google as perform_auth
    from .auth import auth_google_manual
    from .config import add_provider_config
    
    try:
        if client_id and client_secret:
            msg = auth_google_manual(client_id, client_secret)
        else:
            typer.echo("Bitte kopiere den INHALT der Google JSON-Datei hier hinein.")
            typer.echo("Drücke danach STRG+D zum Speichern.")
            json_data = sys.stdin.read().strip()
            if not json_data:
                typer.echo("Abbruch: Keine Daten empfangen.")
                return
            msg = perform_auth(json_data)
        
        add_provider_config("google", label)
        typer.echo(f"✅ {msg}")
        typer.echo(f"✅ Provider registriert unter Label: {label}")
    except Exception as e:
        typer.echo(f"❌ Fehler: {e}")

@app.command()
def auth_microsoft(
    client_id: str, 
    tenant_id: str = "common",
    label: str = typer.Option("MS", help="Account label (e.g. Privat, FH)")
):
    """Save Microsoft App Registration ID."""
    from .auth import auth_microsoft as perform_auth
    from .config import add_provider_config
    msg = perform_auth(client_id, tenant_id)
    add_provider_config("microsoft", label)
    typer.echo(f"✅ {msg}")
    typer.echo(f"✅ Provider registriert unter Label: {label}")

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
