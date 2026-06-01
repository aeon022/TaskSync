from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    list_name: str = Field(default="Reminders", index=True)
    description: Optional[str] = None
    status: str = Field(default="needsAction") # "needsAction" or "completed"
    due_date: Optional[datetime] = None
    recurrence: Optional[str] = None # "daily", "weekly", "monthly"
    sync_pending: bool = Field(default=False) # True if modified locally but not yet synced
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    source_provider: Optional[str] = None # Which provider "owns" this task locally

class TaskTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    title: str
    description: Optional[str] = None
    list_name: Optional[str] = None

class SyncMapping(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    provider_name: str
    remote_id: str
    last_sync: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SyncLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    event: str # e.g. "LOCAL_UPDATE", "REMOTE_UPDATE", "CONFLICT_RESOLVED"
    details: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskList(SQLModel, table=True):
    """Local cache for list names to enable instant startup."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    provider_name: str
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
