import os
from pathlib import Path
from sqlmodel import create_engine, Session, SQLModel, select
from typing import List, Optional
from .models import Task, SyncMapping

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
            # 1. Fetch remote tasks
            remote_tasks = provider.get_tasks()
            
            with get_session() as session:
                for remote_task in remote_tasks:
                    # Check if this remote task is already mapped
                    mapping = session.exec(
                        select(SyncMapping).where(
                            SyncMapping.provider_name == provider.name,
                            SyncMapping.remote_id == remote_task.remote_id
                        )
                    ).first()
                    
                    if mapping:
                        # Update existing local task if needed (simplified "latest wins")
                        local_task = session.get(Task, mapping.task_id)
                        if remote_task.last_modified > local_task.last_modified:
                            local_task.title = remote_task.title
                            local_task.status = remote_task.status
                            local_task.last_modified = remote_task.last_modified
                            session.add(local_task)
                    else:
                        # Create new local task and mapping
                        new_task = Task(
                            title=remote_task.title,
                            status=remote_task.status,
                            last_modified=remote_task.last_modified
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
        
        # 2. Propagate local changes to other providers (simplified)
        self._propagate_to_remotes()

    def _propagate_to_remotes(self):
        """Propagate tasks to providers that don't have them yet."""
        with get_session() as session:
            tasks = session.exec(select(Task)).all()
            for task in tasks:
                for provider in self.providers:
                    # Check if mapping exists for this provider
                    mapping = session.exec(
                        select(SyncMapping).where(
                            SyncMapping.task_id == task.id,
                            SyncMapping.provider_name == provider.name
                        )
                    ).first()
                    
                    if not mapping:
                        # Create task on remote provider
                        remote_id = provider.create_task(task)
                        if remote_id:
                            new_mapping = SyncMapping(
                                task_id=task.id,
                                provider_name=provider.name,
                                remote_id=remote_id
                            )
                            session.add(new_mapping)
            session.commit()
