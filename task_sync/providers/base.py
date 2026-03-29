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
    
    def get_tasks(self) -> List[RemoteTask]:
        ...
        
    def get_lists(self) -> List[str]:
        ...
        
    def create_task(self, task) -> str:
        ...
        
    def update_task(self, remote_id: str, task) -> bool:
        ...
        
    def delete_task(self, remote_id: str) -> bool:
        ...
        
    def create_list(self, name: str) -> bool:
        ...
        
    def delete_list(self, name: str) -> bool:
        ...
        
    def rename_list(self, old_name: str, new_name: str) -> bool:
        ...
