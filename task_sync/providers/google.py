import asyncio
from typing import List, Optional
from datetime import datetime
import logging
from .base import RemoteTask, Provider
from ..security import save_secret, load_secret
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json

# Setup logger for provider
logger = logging.getLogger("utaskd")

SCOPES = ['https://www.googleapis.com/auth/tasks']

class GoogleTasksProvider:
    name = "google"

    def __init__(self, account_label: str = "Google"):
        self.account_label = account_label
        self.creds = self._load_creds()
        self.service = None
        if self.creds:
            self.service = build('tasks', 'v1', credentials=self.creds, static_discovery=False)

    def _load_creds(self) -> Optional[Credentials]:
        token_data = load_secret("google", "token")
        if token_data:
            return Credentials.from_authorized_user_info(token_data, SCOPES)
        return None

    def _save_creds(self, creds: Credentials):
        save_secret("google", "token", json.loads(creds.to_json()))

    async def _refresh_if_needed(self):
        if self.creds and self.creds.expired and self.creds.refresh_token:
            logger.info("Refreshing Google OAuth token...")
            await asyncio.to_thread(self.creds.refresh, Request())
            self._save_creds(self.creds)

    async def get_tasks(self, list_name: Optional[str] = None) -> List[RemoteTask]:
        if not self.service: return []
        await self._refresh_if_needed()
        
        list_id = "@default"
        if list_name:
            lists = await self.get_lists_raw()
            target = next((l for l in lists if l['title'].lower() == list_name.lower()), None)
            if target: 
                list_id = target['id']
            else:
                logger.warning(f"Google Tasks: List '{list_name}' not found, falling back to @default")

        try:
            results = await asyncio.to_thread(
                self.service.tasks().list(tasklist=list_id, showCompleted=True, showHidden=True).execute
            )
            items = results.get('items', [])
            return [RemoteTask(
                remote_id=item['id'],
                title=item['title'],
                status=item['status'],
                list_name=list_name or 'Google Tasks',
                last_modified=datetime.fromisoformat(item['updated'].replace('Z', '+00:00'))
            ) for item in items]
        except Exception as e:
            logger.error(f"Google Tasks Error fetching tasks: {e}")
            return []

    async def get_lists(self) -> List[str]:
        lists = await self.get_lists_raw()
        titles = [l['title'] for l in lists]
        logger.info(f"Google Tasks: Found lists: {titles}")
        return titles

    async def get_lists_raw(self) -> List[dict]:
        if not self.service: 
            logger.error("Google Tasks: Service not initialized (No credentials?)")
            return []
        await self._refresh_if_needed()
        try:
            results = await asyncio.to_thread(self.service.tasklists().list().execute)
            return results.get('items', [])
        except Exception as e:
            logger.error(f"Google Tasks: Error fetching raw lists: {e}")
            return []

    async def create_task(self, title: str, list_name: str) -> Optional[str]:
        if not self.service: return None
        await self._refresh_if_needed()
        
        lists = await self.get_lists_raw()
        target = next((l for l in lists if l['title'].lower() == list_name.lower()), None)
        list_id = target['id'] if target else "@default"
        
        try:
            result = await asyncio.to_thread(
                self.service.tasks().insert(tasklist=list_id, body={'title': title}).execute
            )
            return result['id']
        except Exception as e:
            logger.error(f"Google Tasks: Error creating task: {e}")
            return None

    async def update_task(self, remote_id: str, title: Optional[str] = None, status: Optional[str] = None) -> bool:
        if not self.service: return False
        await self._refresh_if_needed()
        
        lists = await self.get_lists_raw()
        
        body = {'id': remote_id}
        if title: body['title'] = title
        if status: 
            # Google Tasks: 'completed' or 'needsAction'
            body['status'] = status
            if status == "completed":
                # When completing, Google often expects a completed timestamp
                body['completed'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            else:
                body['completed'] = None # Re-open

        for l in lists:
            try:
                result = await asyncio.to_thread(
                    self.service.tasks().patch(tasklist=l['id'], task=remote_id, body=body).execute
                )
                logger.info(f"Google Tasks: Updated {remote_id} in list {l['id']}. Response Status: {result.get('status')}")
                return True
            except Exception as e:
                # If the task isn't in this list, Google returns 404, we just continue searching
                continue
        logger.error(f"Google Tasks: Could not find task {remote_id} in any list to update status.")
        return False

    async def delete_task(self, remote_id: str) -> bool:
        if not self.service: return False
        await self._refresh_if_needed()
        lists = await self.get_lists_raw()
        for l in lists:
            try:
                await asyncio.to_thread(
                    self.service.tasks().delete(tasklist=l['id'], task=remote_id).execute
                )
                return True
            except:
                continue
        return False

    async def create_list(self, name: str) -> bool:
        if not self.service: return False
        await self._refresh_if_needed()
        try:
            logger.info(f"Google Tasks: Creating new list '{name}'")
            await asyncio.to_thread(
                self.service.tasklists().insert(body={'title': name}).execute
            )
            return True
        except Exception as e:
            logger.error(f"Google Tasks: Failed to create list '{name}': {e}")
            return False

    async def rename_list(self, old_name: str, new_name: str) -> bool:
        if not self.service: return False
        await self._refresh_if_needed()
        lists = await self.get_lists_raw()
        target = next((l for l in lists if l['title'] == old_name), None)
        if not target: return False
        try:
            await asyncio.to_thread(
                self.service.tasklists().patch(tasklist=target['id'], body={'title': new_name}).execute
            )
            return True
        except: return False

    async def delete_list(self, name: str) -> bool:
        if not self.service: return False
        await self._refresh_if_needed()
        lists = await self.get_lists_raw()
        target = next((l for l in lists if l['title'] == name), None)
        if not target: return False
        try:
            await asyncio.to_thread(
                self.service.tasklists().delete(tasklist=target['id']).execute
            )
            return True
        except: return False
