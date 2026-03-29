import os
from pathlib import Path
from sqlmodel import create_engine, Session, SQLModel, select
from typing import List, Optional
from .models import Task, SyncMapping
from datetime import datetime, timezone

# Default config directory
CONFIG_DIR = Path.home() / ".config" / "utask"
DB_PATH = CONFIG_DIR / "state.db"
os.makedirs(CONFIG_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}")

_db_initialized = False

def init_db():
    global _db_initialized
    if _db_initialized:
        return
    print(f"Initializing database at {DB_PATH}...")
    SQLModel.metadata.create_all(engine)
    
    # Simple migration: Add list_name column if it doesn't exist
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("ALTER TABLE task ADD COLUMN list_name VARCHAR DEFAULT 'Reminders'"))
            conn.commit()
    except:
        pass
        
    _db_initialized = True

def get_session():
    init_db()
    return Session(engine)

class SyncEngine:
    def __init__(self, providers):
        self.providers = providers # List of Provider objects
        init_db()

    def sync(self):
        """Main sync loop."""
        for provider in self.providers:
            # Fetch all lists for this provider
            try:
                lists = provider.get_lists()
            except:
                lists = ["Reminders"]
            
            if not lists:
                lists = ["Reminders"]

            for list_name in lists:
                # Temporarily set the list for the provider
                old_list = getattr(provider, "_list_name", None)
                if hasattr(provider, "_list_name"):
                    provider._list_name = list_name
                
                try:
                    remote_tasks = provider.get_tasks()
                except:
                    remote_tasks = []
                
                with get_session() as session:
                    for remote_task in remote_tasks:
                        mapping = session.exec(
                            select(SyncMapping).where(
                                SyncMapping.provider_name == provider.name,
                                SyncMapping.remote_id == remote_task.remote_id
                            )
                        ).first()
                        
                        # Normalize timestamps for comparison (strip timezone)
                        remote_mod = remote_task.last_modified.replace(tzinfo=None) if remote_task.last_modified.tzinfo else remote_task.last_modified
                        
                        if mapping:
                            local_task = session.get(Task, mapping.task_id)
                            if local_task:
                                local_mod = local_task.last_modified.replace(tzinfo=None) if local_task.last_modified.tzinfo else local_task.last_modified
                                
                                if remote_mod > local_mod:
                                    local_task.title = remote_task.title
                                    local_task.status = remote_task.status
                                    local_task.list_name = remote_task.list_name
                                    local_task.last_modified = remote_mod
                                    session.add(local_task)
                        else:
                            new_task = Task(
                                title=remote_task.title,
                                status=remote_task.status,
                                list_name=remote_task.list_name,
                                last_modified=remote_mod
                            )
                            session.add(new_task)
                            session.commit()
                            session.refresh(new_task)
                            
                            new_mapping = SyncMapping(
                                task_id=new_task.id,
                                provider_name=provider.name,
                                remote_id=remote_task.remote_id
                            )
                            session.add(new_mapping)
                    session.commit()
                
                # Restore provider list if needed
                if hasattr(provider, "_list_name"):
                    provider._list_name = old_list
        
        # 2. Propagate local changes to other providers
        self._propagate_to_remotes()

    def _propagate_to_remotes(self):
        """Propagate tasks to providers that don't have them yet."""
        with get_session() as session:
            tasks = session.exec(select(Task)).all()
            for task in tasks:
                for provider in self.providers:
                    mapping = session.exec(
                        select(SyncMapping).where(
                            SyncMapping.task_id == task.id,
                            SyncMapping.provider_name == provider.name
                        )
                    ).first()
                    
                    if not mapping:
                        try:
                            remote_id = provider.create_task(task)
                            if remote_id:
                                new_mapping = SyncMapping(
                                    task_id=task.id,
                                    provider_name=provider.name,
                                    remote_id=remote_id
                                )
                                session.add(new_mapping)
                        except:
                            pass
            session.commit()
