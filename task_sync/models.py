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
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    source_provider: Optional[str] = None # Which provider "owns" this task locally

class SyncMapping(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    provider_name: str
    remote_id: str
    last_sync: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskList(SQLModel, table=True):
    """Local cache for list names to enable instant startup."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    provider_name: str
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
