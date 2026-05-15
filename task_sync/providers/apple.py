import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from .base import RemoteTask, Provider
from .. import api_apple

class AppleRemindersProvider(Provider):
    name = "apple"

    def __init__(self, account_label: str = "Apple"):
        self.account_label = account_label

    def is_authenticated(self) -> bool:
        return api_apple.is_mac()

    async def get_tasks(self, list_name: Optional[str] = None) -> List[RemoteTask]:
        # api_apple is sync/callback based, wrap in thread
        effective_list = list_name or "Reminders"
        tasks = await asyncio.to_thread(api_apple.get_tasks, effective_list)
        return [RemoteTask(
            remote_id=t["id"],
            title=t["title"],
            status="completed" if t["completed"] else "needsAction",
            list_name=effective_list,
            last_modified=datetime.now(timezone.utc) # EventKit is tricky with modification dates
        ) for t in tasks]

    async def get_lists(self) -> List[str]:
        return await asyncio.to_thread(api_apple.get_lists)

    async def create_task(self, title: str, list_name: str) -> Optional[str]:
        return await asyncio.to_thread(api_apple.create_task, title, list_name)

    async def update_task(self, remote_id: str, title: Optional[str] = None, status: Optional[str] = None) -> bool:
        completed = None
        if status is not None:
            completed = (status == "completed")
        return await asyncio.to_thread(api_apple.update_task, remote_id, title, completed)

    async def delete_task(self, remote_id: str) -> bool:
        return False

    async def create_list(self, name: str) -> bool:
        return False
    
    async def delete_list(self, name: str) -> bool:
        return await asyncio.to_thread(api_apple.delete_list, name)

    async def rename_list(self, old_name: str, new_name: str) -> bool:
        return False
