import typer
import warnings
import os
from typing import Optional
from sqlmodel import select

# Suppress annoying Google API warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from .core import SyncEngine, get_session, init_db
from .models import Task, SyncMapping
from .providers.apple import AppleRemindersProvider
from .providers.google import GoogleTasksProvider

app = typer.Typer(
    help="UniversalTask CLI - Sync tasks across Apple, Google, and Outlook.",
    add_completion=False,
    no_args_is_help=True
)

@app.callback()
def callback():
    """Initialize UniversalTask CLI."""
    try:
        init_db()
    except Exception as e:
        typer.secho(f"Database error: {e}", fg=typer.colors.RED, err=True)

def get_engine(list_name: Optional[str] = None):
    providers = []
    
    if os.uname().sysname == 'Darwin':
        providers.append(AppleRemindersProvider(list_name=list_name))
        
    google = GoogleTasksProvider()
    if google.is_authenticated():
        providers.append(google)
        
    return SyncEngine(providers)

@app.command()
def auth(provider: str = typer.Argument(..., help="Name of the provider (e.g. 'google')")):
    """Authenticate with a remote provider."""
    if provider.lower() == "google":
        typer.echo("🔗 Opening browser for Google Tasks login...")
        google = GoogleTasksProvider()
        if google.run_login_flow():
            typer.secho("✅ Google Tasks authentication successful!", fg=typer.colors.GREEN)
        else:
            typer.secho("❌ Authentication failed. Make sure 'credentials.json' is present for now.", fg=typer.colors.RED)
    else:
        typer.echo(f"Unknown provider: {provider}")

@app.command()
def sync(list_name: Optional[str] = typer.Option(None, "--list", help="Name of the Apple Reminders list.")):
    """Synchronize tasks across all enabled providers."""
    typer.echo("🔄 Syncing tasks...")
    try:
        engine = get_engine(list_name=list_name)
        engine.sync()
        typer.secho("✨ Sync complete!", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"❌ Sync failed: {e}", fg=typer.colors.RED, err=True)

@app.command()
def list(all: bool = typer.Option(False, "--all", "-a", help="Show all tasks, including completed ones.")):
    """List synchronized tasks (only pending by default)."""
    with get_session() as session:
        if all:
            tasks = session.exec(select(Task)).all()
        else:
            tasks = session.exec(select(Task).where(Task.status == "needsAction")).all()
            
        if not tasks:
            typer.echo("No pending tasks found. Use 'utask add' to create one or '--all' to see completed tasks.")
            return
            
        typer.echo("\n📋 Your Tasks:")
        for task in tasks:
            status_icon = "✅" if task.status == "completed" else "⭕"
            typer.echo(f"  {task.id}: {status_icon} {task.title}")
        typer.echo("")

@app.command()
def complete(task_id: int):
    """Check off (complete) a task on all providers."""
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            typer.secho(f"Task {task_id} not found.", fg=typer.colors.RED)
            return
        
        task.status = "completed"
        session.add(task)
        
        engine = get_engine()
        # Update remotes
        mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
        for mapping in mappings:
            for provider in engine.providers:
                if provider.name == mapping.provider_name:
                    provider.update_task(mapping.remote_id, task)
        
        session.commit()
        typer.secho(f"✅ Completed task {task_id}: {task.title}", fg=typer.colors.GREEN)

@app.command()
def add(
    title: str, 
    list_name: Optional[str] = typer.Option(None, "--list", help="Name of the Apple Reminders list.")
):
    """Add a new task to all providers."""
    with get_session() as session:
        new_task = Task(title=title)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        typer.secho(f"➕ Added task: {new_task.title}", fg=typer.colors.CYAN)
        
    sync(list_name=list_name)

@app.command()
def delete(task_id: int):
    """Delete a task from all providers."""
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            typer.secho(f"Task {task_id} not found.", fg=typer.colors.RED)
            return
        
        engine = get_engine()
        # Find mappings to delete from remotes
        mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
        for mapping in mappings:
            for provider in engine.providers:
                if provider.name == mapping.provider_name:
                    provider.delete_task(mapping.remote_id)
            session.delete(mapping)
        
        session.delete(task)
        session.commit()
        typer.secho(f"🗑️ Deleted task {task_id}", fg=typer.colors.YELLOW)

@app.command()
def rename(task_id: int, new_title: str):
    """Rename (update) a task title."""
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            typer.secho(f"Task {task_id} not found.", fg=typer.colors.RED)
            return
        
        task.title = new_title
        session.add(task)
        
        engine = get_engine()
        # Update remotes
        mappings = session.exec(select(SyncMapping).where(SyncMapping.task_id == task_id)).all()
        for mapping in mappings:
            for provider in engine.providers:
                if provider.name == mapping.provider_name:
                    provider.update_task(mapping.remote_id, task)
        
        session.commit()
        typer.secho(f"📝 Renamed task {task_id} to: {new_title}", fg=typer.colors.CYAN)

# List Management Commands
list_app = typer.Typer(help="Manage task lists (Reminders lists, Google TaskLists).")
app.add_typer(list_app, name="list-mgnt")

@app.command()
def ui():
    """Launch the interactive Terminal User Interface (TUI)."""
    from .tui import UniversalTaskApp
    app = UniversalTaskApp()
    app.run()

@list_app.command("create")
def create_list(name: str):
    """Create a new task list on all providers."""
    engine = get_engine()
    for provider in engine.providers:
        if provider.create_list(name):
            typer.echo(f"✅ Created list '{name}' on {provider.name}")
        else:
            typer.echo(f"❌ Failed to create list '{name}' on {provider.name}")

@list_app.command("delete")
def delete_list(name: str):
    """Delete a task list from all providers."""
    if not typer.confirm(f"Are you sure you want to delete the list '{name}' and ALL its tasks?"):
        return
    engine = get_engine()
    for provider in engine.providers:
        if provider.delete_list(name):
            typer.echo(f"🗑️ Deleted list '{name}' from {provider.name}")
        else:
            typer.echo(f"❌ Failed to delete list '{name}' from {provider.name}")

@list_app.command("rename")
def rename_list(old_name: str, new_name: str):
    """Rename a task list on all providers."""
    engine = get_engine()
    for provider in engine.providers:
        if provider.rename_list(old_name, new_name):
            typer.echo(f"📝 Renamed list '{old_name}' to '{new_name}' on {provider.name}")
        else:
            typer.echo(f"❌ Failed to rename list on {provider.name}")

if __name__ == "__main__":
    app()
