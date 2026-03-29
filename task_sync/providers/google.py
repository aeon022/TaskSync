import os.path
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import List, Optional
from datetime import datetime
from .base import RemoteTask, Provider
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/tasks']

class GoogleTasksProvider:
    name = "google"

    def __init__(self):
        config_dir = Path.home() / ".config" / "utask"
        os.makedirs(config_dir, exist_ok=True)
        self.token_path = str(config_dir / "google_token.pickle")
        # Wir suchen die credentials.json NUR im Projektordner oder im Config-Ordner
        self.creds_path = 'credentials.json'
        if not os.path.exists(self.creds_path):
            self.creds_path = str(config_dir / "credentials.json")
            
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                try: creds = pickle.load(token)
                except: creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(creds, token)
                except: return None
            else: return None

        return build('tasks', 'v1', credentials=creds, static_discovery=False)

    def is_authenticated(self) -> bool:
        return self.service is not None

    def run_login_flow(self):
        """Startet den Browser-Login. Erfordert die credentials.json im Ordner."""
        try:
            if not os.path.exists(self.creds_path):
                return "MISSING_FILE"

            flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
            creds = flow.run_local_server(port=0, title="UniversalTask Google Login")
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
            
            self.service = build('tasks', 'v1', credentials=creds, static_discovery=False)
            return "SUCCESS"
        except Exception as e:
            print(f"Login Fehler: {e}")
            return "ERROR"

    def get_tasks(self) -> List[RemoteTask]:
        if not self.service: return []
        try:
            results = self.service.tasks().list(tasklist='@default').execute()
            items = results.get('items', [])
            return [RemoteTask(
                remote_id=item['id'],
                title=item['title'],
                status=item['status'],
                list_name='Google Tasks',
                last_modified=datetime.fromisoformat(item['updated'].replace('Z', '+00:00'))
            ) for item in items]
        except: return []

    def create_task(self, task) -> str:
        if not self.service: return ""
        try:
            result = self.service.tasks().insert(tasklist='@default', body={'title': task.title}).execute()
            return result['id']
        except: return ""

    def update_task(self, remote_id: str, task) -> bool:
        if not self.service: return False
        try:
            self.service.tasks().update(tasklist='@default', task=remote_id, body={
                'id': remote_id, 'title': task.title, 'status': task.status
            }).execute()
            return True
        except: return False

    def delete_task(self, remote_id: str) -> bool:
        if not self.service: return False
        try:
            self.service.tasks().delete(tasklist='@default', task=remote_id).execute()
            return True
        except: return False

    def get_lists(self) -> List[str]:
        if not self.service: return []
        try:
            results = self.service.tasklists().list().execute()
            return [l['title'] for l in results.get('items', [])]
        except: return []

    def create_list(self, name: str) -> bool:
        if not self.service: return False
        try:
            self.service.tasklists().insert(body={'title': name}).execute()
            return True
        except: return False
