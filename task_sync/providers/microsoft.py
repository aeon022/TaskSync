import asyncio
import aiohttp
import msal
from typing import List, Optional
from datetime import datetime
from .base import RemoteTask, Provider
from ..security import save_secret, load_secret

SCOPES = ['Tasks.ReadWrite']

class MicrosoftToDoProvider:
    name = "microsoft"

    def __init__(self, account_label: str = "MS"):
        self.account_label = account_label
        self.client_id = load_secret("microsoft", "client_id", is_json=False)
        self.tenant_id = load_secret("microsoft", "tenant_id", is_json=False) or "common"
        self.app = None
        if self.client_id:
            self.app = msal.PublicClientApplication(
                self.client_id, 
                authority=f"https://login.microsoftonline.com/{self.tenant_id}"
            )

    async def _get_access_token(self) -> Optional[str]:
        if not self.app: return None
        
        accounts = self.app.get_accounts()
        if accounts:
            # Note: MSAL's acquire_token_silent is sync
            result = await asyncio.to_thread(self.app.acquire_token_silent, SCOPES, account=accounts[0])
            if result and 'access_token' in result:
                return result['access_token']
        return None

    async def _headers(self):
        token = await self._get_access_token()
        if not token: return {}
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    async def get_tasks(self, list_name: Optional[str] = None) -> List[RemoteTask]:
        headers = await self._headers()
        if not headers: return []
        
        async with aiohttp.ClientSession() as session:
            # Default to 'tasks' list if no list_name provided
            list_id = "tasks"
            if list_name:
                lists = await self._get_lists_raw(session, headers)
                target = next((l for l in lists if l['displayName'] == list_name), None)
                if target: list_id = target['id']

            async with session.get(f'https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks', headers=headers) as r:
                if r.status != 200: return []
                data = await r.json()
                items = data.get('value', [])
                return [RemoteTask(
                    remote_id=item['id'],
                    title=item['title'],
                    status='completed' if item['status'] == 'completed' else 'needsAction',
                    list_name=list_name or 'Microsoft To Do',
                    last_modified=datetime.fromisoformat(item['lastModifiedDateTime'].replace('Z', '+00:00'))
                ) for item in items]

    async def _get_lists_raw(self, session, headers) -> List[dict]:
        async with session.get('https://graph.microsoft.com/v1.0/me/todo/lists', headers=headers) as r:
            if r.status != 200: return []
            data = await r.json()
            return data.get('value', [])

    async def get_lists(self) -> List[str]:
        headers = await self._headers()
        if not headers: return []
        async with aiohttp.ClientSession() as session:
            lists = await self._get_lists_raw(session, headers)
            return [l['displayName'] for l in lists]

    async def create_task(self, title: str, list_name: str) -> Optional[str]:
        headers = await self._headers()
        if not headers: return None
        
        async with aiohttp.ClientSession() as session:
            lists = await self._get_lists_raw(session, headers)
            target = next((l for l in lists if l['displayName'] == list_name), None)
            list_id = target['id'] if target else "tasks"
            
            body = {'title': title}
            async with session.post(f'https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks', headers=headers, json=body) as r:
                if r.status == 201:
                    data = await r.json()
                    return data.get('id')
        return None

    async def update_task(self, remote_id: str, title: Optional[str] = None, status: Optional[str] = None) -> bool:
        headers = await self._headers()
        if not headers: return False
        
        body = {}
        if title: body['title'] = title
        if status: body['status'] = 'completed' if status == 'completed' else 'notStarted'

        async with aiohttp.ClientSession() as session:
            # Note: We need the list_id here too. For now assume 'tasks'
            async with session.patch(f'https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{remote_id}', headers=headers, json=body) as r:
                return r.status == 200
        return False

    async def delete_task(self, remote_id: str) -> bool:
        headers = await self._headers()
        if not headers: return False
        async with aiohttp.ClientSession() as session:
            async with session.delete(f'https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{remote_id}', headers=headers) as r:
                return r.status == 204

    async def create_list(self, name: str) -> bool:
        headers = await self._headers()
        if not headers: return False
        async with aiohttp.ClientSession() as session:
            payload = {"displayName": name}
            async with session.post('https://graph.microsoft.com/v1.0/me/todo/lists', headers=headers, json=payload) as r:
                return r.status == 201

    async def delete_list(self, name: str) -> bool:
        headers = await self._headers()
        if not headers: return False
        async with aiohttp.ClientSession() as session:
            lists = await self._get_lists_raw(session, headers)
            target = next((l for l in lists if l['displayName'] == name), None)
            if not target: return False
            async with session.delete(f"https://graph.microsoft.com/v1.0/me/todo/lists/{target['id']}", headers=headers) as r:
                return r.status == 204

    async def rename_list(self, old_name: str, new_name: str) -> bool:
        return False
