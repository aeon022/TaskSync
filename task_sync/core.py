import os
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlmodel import SQLModel, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import Task, SyncMapping, TaskList

# Default config directory
CONFIG_DIR = Path.home() / ".config" / "tasksync"
LOG_FILE = CONFIG_DIR / "daemon.log"
os.makedirs(CONFIG_DIR, exist_ok=True)

# Logging Setup
logger = logging.getLogger("utaskd")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

DATABASE_URL = f"sqlite+aiosqlite:///{CONFIG_DIR / 'state.db'}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

class SyncEngine:
    def __init__(self, providers: List[Any]):
        self.providers = providers

    def _get_display_name(self, label: str, list_name: str) -> str:
        return f"[{label}] {list_name}"

    async def sync_all(self):
        """Full synchronization across all providers with Account Prefixes."""
        logger.info("Starting prefixed sync...")
        
        all_remote_display_names = set()
        successful_providers = []
        
        async with AsyncSessionLocal() as session:
            for provider in self.providers:
                try:
                    lists = await provider.get_lists()
                    successful_providers.append(provider)
                    for l_name in lists:
                        display_name = self._get_display_name(provider.account_label, l_name)
                        all_remote_display_names.add(display_name)
                        
                        # Sync tasks for this specific account list
                        remote_tasks = await provider.get_tasks(list_name=l_name)
                        await self._update_local_db(provider.name, remote_tasks, display_name)
                except Exception as e:
                    logger.error(f"Error syncing {provider.name}: {e}")

            # Cleanup orphaned lists/tasks ONLY for providers that were successfully contacted
            local_lists_res = await session.execute(select(TaskList.name))
            current_local_lists = set(local_lists_res.scalars().all())
            
            # Identify lists that should be checked for deletion
            # (only those belonging to successful providers)
            check_prefixes = [f"[{p.account_label}]" for p in successful_providers]
            
            deleted_everywhere = []
            for local_name in current_local_lists:
                # If this list belongs to a provider we successfully synced...
                if any(local_name.startswith(pre) for pre in check_prefixes):
                    # ...but it's not in the remote list anymore, mark for deletion
                    if local_name not in all_remote_display_names:
                        deleted_everywhere.append(local_name)

            for d_name in deleted_everywhere:
                await session.execute(delete(Task).where(Task.list_name == d_name))
                await session.execute(delete(TaskList).where(TaskList.name == d_name))

            # Rebuild TaskList cache
            await session.execute(delete(TaskList))
            # Note: This is still slightly aggressive as it wipes the whole TaskList table.
            # Let's keep existing lists for failed providers.
            final_lists = all_remote_display_names.copy()
            for local_name in current_local_lists:
                if not any(local_name.startswith(pre) for pre in check_prefixes):
                    final_lists.add(local_name)

            for name in sorted(final_lists):
                session.add(TaskList(name=name, provider_name="multi"))
            await session.commit()

        await self._propagate()
        logger.info("Sync complete.")

    async def _update_local_db(self, provider_name: str, remote_tasks: List[Any], display_name: str):
        now_utc = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            # We only want to look at mappings that belong to this list and provider
            mapping_stmt = select(SyncMapping).join(Task).where(
                SyncMapping.provider_name == provider_name,
                Task.list_name == display_name
            )
            mapping_res = await session.execute(mapping_stmt)
            existing_mappings = {m.remote_id: m for m in mapping_res.scalars().all()}
            
            seen_remote_ids = set()
            for rt in remote_tasks:
                seen_remote_ids.add(rt.remote_id)
                mapping = existing_mappings.get(rt.remote_id)
                rt_modified = rt.last_modified.replace(tzinfo=timezone.utc) if rt.last_modified.tzinfo is None else rt.last_modified
                
                if mapping:
                    task = await session.get(Task, mapping.task_id)
                    if task:
                        task_modified = task.last_modified.replace(tzinfo=timezone.utc) if task.last_modified.tzinfo is None else task.last_modified
                        if rt_modified > task_modified:
                            task.status = rt.status
                            task.title = rt.title
                            task.last_modified = rt_modified
                            task.list_name = display_name
                            session.add(task)
                        mapping.last_sync = now_utc
                        session.add(mapping)
                else:
                    # Check if this task exists under a different list/provider (conflict/move)
                    # For now, just create new
                    new_task = Task(
                        title=rt.title, 
                        status=rt.status, 
                        list_name=display_name, 
                        last_modified=rt_modified, 
                        source_provider=provider_name
                    )
                    session.add(new_task)
                    await session.flush()
                    session.add(SyncMapping(task_id=new_task.id, provider_name=provider_name, remote_id=rt.remote_id, last_sync=now_utc))
            
            # Local deletions: only delete if task was in THIS list but is now gone from remote
            deleted_ids = set(existing_mappings.keys()) - seen_remote_ids
            for rid in deleted_ids:
                mapping = existing_mappings[rid]
                task = await session.get(Task, mapping.task_id)
                if task:
                    await session.delete(task)
                await session.delete(mapping)
            await session.commit()

    async def _propagate(self):
        """Propagate local changes back to remotes, stripping prefixes for API calls."""
        now_utc = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Task))
            tasks = result.scalars().all()
            
            for task in tasks:
                task_modified = task.last_modified.replace(tzinfo=timezone.utc) if task.last_modified.tzinfo is None else task.last_modified
                
                # Extract real list name by removing prefix like "[FH] "
                real_list_name = task.list_name
                if "]" in task.list_name:
                    real_list_name = task.list_name.split("]", 1)[1].strip()

                for provider in self.providers:
                    # We only propagate to the provider that matches the prefix
                    expected_prefix = f"[{provider.account_label}]"
                    if not task.list_name.startswith(expected_prefix):
                        continue

                    map_res = await session.execute(select(SyncMapping).where(
                        SyncMapping.task_id == task.id, 
                        SyncMapping.provider_name == provider.name
                    ))
                    mapping = map_res.scalar_one_or_none()
                    
                    if not mapping:
                        try:
                            remote_id = await provider.create_task(task.title, real_list_name)
                            if remote_id:
                                session.add(SyncMapping(task_id=task.id, provider_name=provider.name, remote_id=remote_id, last_sync=now_utc))
                                if task.status == "completed":
                                    await provider.update_task(remote_id, status="completed")
                        except Exception as e:
                            logger.error(f"Failed creation propagate: {e}")
                    else:
                        last_sync = mapping.last_sync.replace(tzinfo=timezone.utc) if mapping.last_sync.tzinfo is None else mapping.last_sync
                        if task_modified > last_sync:
                            try:
                                if await provider.update_task(mapping.remote_id, title=task.title, status=task.status):
                                    mapping.last_sync = now_utc
                                    session.add(mapping)
                            except Exception as e:
                                logger.error(f"Failed update propagate: {e}")
            await session.commit()

    async def delete_list(self, display_name: str):
        """Deletes a list globally based on display name."""
        real_list_name = display_name
        if "]" in display_name:
            real_list_name = display_name.split("]", 1)[1].strip()
        
        for provider in self.providers:
            prefix = f"[{provider.account_label}]"
            if display_name.startswith(prefix):
                try:
                    await provider.delete_list(real_list_name)
                except Exception as e:
                    logger.error(f"Failed to delete remote list: {e}")

        async with AsyncSessionLocal() as session:
            await session.execute(delete(Task).where(Task.list_name == display_name))
            await session.execute(delete(TaskList).where(TaskList.name == display_name))
            await session.commit()

    async def move_tasks(self, task_ids: List[int], target_label: str) -> int:
        """Migrates tasks from their current provider to a new target provider."""
        target_provider = next((p for p in self.providers if p.account_label.lower() == target_label.lower()), None)
        if not target_provider:
            return 0
            
        success_count = 0
        now_utc = datetime.now(timezone.utc)
        
        async with AsyncSessionLocal() as session:
            for task_id in task_ids:
                task = await session.get(Task, task_id)
                if not task: continue
                
                # 1. Find and delete from old provider
                old_mapping_stmt = select(SyncMapping).where(SyncMapping.task_id == task_id)
                old_mapping_res = await session.execute(old_mapping_stmt)
                old_mapping = old_mapping_res.scalar_one_or_none()
                
                if old_mapping:
                    old_provider = next((p for p in self.providers if p.name == old_mapping.provider_name), None)
                    if old_provider:
                        try:
                            await old_provider.delete_task(old_mapping.remote_id)
                        except Exception as e:
                            logger.error(f"Failed to delete task {task_id} from old provider: {e}")
                    await session.delete(old_mapping)
                
                # 2. Create on new provider
                try:
                    # Using a generic "Tasks" list name, providers fallback to default if not found
                    new_remote_id = await target_provider.create_task(task.title, "Tasks")
                    if new_remote_id:
                        # Update task info
                        task.list_name = f"[{target_provider.account_label}] Tasks"
                        task.source_provider = target_provider.name
                        task.last_modified = now_utc
                        session.add(task)
                        
                        # Create new mapping
                        session.add(SyncMapping(
                            task_id=task.id, 
                            provider_name=target_provider.name, 
                            remote_id=new_remote_id, 
                            last_sync=now_utc
                        ))
                        
                        if task.status == "completed":
                            await target_provider.update_task(new_remote_id, status="completed")
                            
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to migrate task {task_id} to {target_label}: {e}")
                    
            await session.commit()
        return success_count

    async def create_list(self, name: str, provider_label: str = "Apple") -> bool:
        """Creates a new list on a specific provider."""
        provider = next((p for p in self.providers if p.account_label.lower() == provider_label.lower()), None)
        if not provider:
            return False
            
        try:
            success = await provider.create_list(name)
            if success:
                async with AsyncSessionLocal() as session:
                    # Add to local cache to make it visible immediately
                    full_name = f"[{provider.account_label}] {name}"
                    session.add(TaskList(name=full_name, provider_name=provider.name))
                    await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to create list '{name}' on {provider_label}: {e}")
            
        return False

async def daemon_loop(engine: SyncEngine, interval: int = 300):
    while True:
        try:
            await engine.sync_all()
        except Exception as e:
            logger.error(f"Daemon Sync Error: {e}")
        await asyncio.sleep(interval)
