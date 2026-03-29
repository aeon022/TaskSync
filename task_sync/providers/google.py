import os.path
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import List, Optional
from datetime import datetime
from .base import RemoteTask, Provider

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/tasks']

class GoogleTasksProvider:
    name = "google"

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        return build('tasks', 'v1', credentials=creds)

    def get_tasks(self) -> List[RemoteTask]:
        if not self.service: return []
        results = self.service.tasks().list(tasklist='@default').execute()
        items = results.get('items', [])
        
        remote_tasks = []
        for item in items:
            remote_tasks.append(RemoteTask(
                remote_id=item['id'],
                title=item['title'],
                status=item['status'],
                last_modified=datetime.fromisoformat(item['updated'].replace('Z', '+00:00'))
            ))
        return remote_tasks

    def create_task(self, task) -> str:
        if not self.service: return ""
        task_body = {'title': task.title}
        result = self.service.tasks().insert(tasklist='@default', body=task_body).execute()
        return result['id']

    def update_task(self, remote_id: str, task) -> bool:
        if not self.service: return False
        task_body = {'id': remote_id, 'title': task.title, 'status': task.status}
        self.service.tasks().update(tasklist='@default', task=remote_id, body=task_body).execute()
        return True

    def delete_task(self, remote_id: str) -> bool:
        if not self.service: return False
        self.service.tasks().delete(tasklist='@default', task=remote_id).execute()
        return True

    def create_list(self, name: str) -> bool:
        # Google Tasks uses 'tasklists'
        if not self.service: return False
        body = {'title': name}
        self.service.tasklists().insert(body=body).execute()
        return True

    def delete_list(self, name: str) -> bool:
        # Simplified: search by name and delete
        return False

    def rename_list(self, old_name: str, new_name: str) -> bool:
        return False
