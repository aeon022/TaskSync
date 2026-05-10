from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Protocol
from pydantic import BaseModel

class RemoteTask(BaseModel):
    remote_id: str
    title: str
    status: str
    list_name: str
    last_modified: datetime

class Provider(Protocol):
    name: str
    account_label: str = "" # e.g. "FH", "Privat", "Apple"
    
    async def get_tasks(self, list_name: Optional[str] = None) -> List[RemoteTask]:
        ...
        
    async def get_lists(self) -> List[str]:
        ...
        
    async def create_task(self, title: str, list_name: str) -> Optional[str]:
        ...
        
    async def update_task(self, remote_id: str, title: Optional[str] = None, status: Optional[str] = None) -> bool:
        ...
        
    async def delete_task(self, remote_id: str) -> bool:
        ...
        
    async def create_list(self, name: str) -> bool:
        ...
        
    async def delete_list(self, name: str) -> bool:
        ...
        
    async def rename_list(self, old_name: str, new_name: str) -> bool:
        ...
