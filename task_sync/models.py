from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    status: str = "needsAction" # "needsAction" or "completed"
    due_date: Optional[datetime] = None
    last_modified: datetime = Field(default_factory=datetime.utcnow)

class SyncMapping(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int
    provider_name: str
    remote_id: str

class TaskList(SQLModel, table=True):
    """Local cache for list names to enable instant startup."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    provider_name: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)
