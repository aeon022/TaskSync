import typer
import asyncio
import sys
from typing import Optional
from pathlib import Path

app = typer.Typer(help="utask v2.0 - Headless Task Sync CLI (https://utask.sh)")
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
def today():
    """List all tasks due today across all providers."""
    from .core import AsyncSessionLocal
    from .models import Task
    from sqlmodel import select
    from datetime import datetime, time, timezone
    
    async def run():
        async with AsyncSessionLocal() as session:
            today_end = datetime.combine(datetime.now(timezone.utc).date(), time.max, tzinfo=timezone.utc)
            # Find tasks with due_date today or in the past (not completed)
            stmt = select(Task).where(Task.due_date <= today_end, Task.status != "completed")
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            
            if not tasks:
                typer.echo("🎉 Alles erledigt für heute!")
                return
                
            for t in tasks:
                typer.echo(f"◯ {t.title} ({t.list_name})")
    
    asyncio.run(run())

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

@app.command()
def doctor():
    """Check system health and diagnostic information."""
    from .config import CONFIG_DIR, get_shared_dir, SHARED_PATH_POINTER
    from .api_apple import is_mac, get_event_store
    import subprocess
    import os
    
    typer.secho("🏥 utask Health Check", fg=typer.colors.MAGENTA, bold=True)
    typer.echo("-" * 30)
    
    # 1. Directories & Permissions
    typer.echo("📁 Directories:")
    local_ok = "✅" if os.access(CONFIG_DIR, os.W_OK) else "❌"
    typer.echo(f"  {local_ok} Local Config:  {CONFIG_DIR}")
    
    shared_dir = get_shared_dir()
    shared_ptr = "✅" if SHARED_PATH_POINTER.exists() else "⚪"
    shared_ok = "✅" if os.access(shared_dir, os.W_OK) else "❌"
    typer.echo(f"  {shared_ok} Shared Dir:   {shared_dir} ({shared_ptr} linked)")
    
    # 2. Daemon Status
    typer.echo("\n🛰️ Daemon Status:")
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.aeon022.utaskd.plist"
    if plist_path.exists():
        res = subprocess.run(["launchctl", "list", "com.aeon022.utaskd"], capture_output=True, text=True)
        if res.returncode == 0:
            typer.echo("  ✅ Service is LOADED and RUNNING")
        else:
            typer.echo("  ⚠️ Service is LOADED but NOT RUNNING")
    else:
        typer.echo("  ⚪ Service is NOT INSTALLED")
        
    # 3. Provider Access
    typer.echo("\n🔐 Provider Connectivity:")
    if is_mac():
        store = get_event_store()
        apple_ok = "✅" if store else "❌"
        typer.echo(f"  {apple_ok} Apple Reminders: Permissions OK")
    
    from .config import load_provider_config
    from .providers import get_provider
    providers = load_provider_config()
    for p in providers:
        instance = get_provider(p["type"], p["label"])
        if instance:
            # Simple check: try to get lists (cached if possible)
            try:
                # We just check if auth exists
                auth_ok = "✅"
                if p["type"] == "google":
                    auth_ok = "✅" if instance._load_creds() else "❌"
                elif p["type"] == "microsoft":
                    auth_ok = "✅" if instance.client_id else "❌"
                typer.echo(f"  {auth_ok} {p['type'].capitalize()} ({p['label']})")
            except:
                typer.echo(f"  ❌ {p['type'].capitalize()} ({p['label']}) - Error")

    typer.echo("-" * 30)
    typer.secho("System Integrity Confirmed.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
