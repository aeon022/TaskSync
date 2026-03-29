import os
import json
import msal
import requests
from typing import List, Optional
from datetime import datetime
from .base import RemoteTask, Provider
from pathlib import Path

# Scopes für Microsoft Graph API (Tasks)
SCOPES = ['Tasks.ReadWrite']

class MicrosoftToDoProvider:
    name = "microsoft"

    def __init__(self):
        config_dir = Path.home() / ".config" / "utask"
        os.makedirs(config_dir, exist_ok=True)
        self.token_path = str(config_dir / "ms_token.json")
        self.creds_path = str(config_dir / "ms_creds.json")
        self.access_token = None
        self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.creds_path):
            return None

        with open(self.creds_path, "r") as f:
            creds = json.load(f)
        
        client_id = creds.get("client_id")
        tenant_id = creds.get("tenant_id", "common")

        app = msal.PublicClientApplication(client_id, authority=f"https://login.microsoftonline.com/{tenant_id}")
        
        # Versuche Token aus Cache zu laden
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result:
                self.access_token = result['access_token']
                return True
        return False

    def is_authenticated(self) -> bool:
        return self.access_token is not None

    def has_app_credentials(self) -> bool:
        return os.path.exists(self.creds_path)

    def save_app_credentials(self, client_id: str, tenant_id: str = "common"):
        config = {"client_id": client_id, "tenant_id": tenant_id}
        with open(self.creds_path, "w") as f:
            json.dump(config, f)

    def run_login_flow(self):
        """Startet den interaktiven Microsoft Login."""
        if not os.path.exists(self.creds_path):
            return "MISSING_FILE"

        with open(self.creds_path, "r") as f:
            creds = json.load(f)
        
        app = msal.PublicClientApplication(creds["client_id"], authority=f"https://login.microsoftonline.com/{creds.get('tenant_id', 'common')}")
        
        # Microsoft nutzt oft den Device Flow für CLIs
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            return "ERROR"

        # Wir geben den Code und die URL zurück, damit das TUI sie anzeigen kann
        return {"code": flow["user_code"], "url": flow["verification_uri"], "flow": flow, "app": app}

    def complete_login(self, flow, app):
        """Wartet auf den Abschluss des Logins."""
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            self.access_token = result['access_token']
            return "SUCCESS"
        return "ERROR"

    def _headers(self):
        return {'Authorization': f'Bearer {self.access_token}', 'Content-Type': 'application/json'}

    def get_tasks(self) -> List[RemoteTask]:
        if not self.access_token: return []
        # Holt Aufgaben aus der Standard-Liste
        r = requests.get('https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks', headers=self._headers())
        if r.status_code != 200: return []
        
        items = r.json().get('value', [])
        return [RemoteTask(
            remote_id=item['id'],
            title=item['title'],
            status='completed' if item['status'] == 'completed' else 'needsAction',
            list_name='Microsoft To Do',
            last_modified=datetime.fromisoformat(item['lastModifiedDateTime'].replace('Z', '+00:00'))
        ) for item in items]

    def create_task(self, task) -> str:
        if not self.access_token: return ""
        body = {'title': task.title}
        r = requests.post('https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks', headers=self._headers(), json=body)
        return r.json().get('id', "") if r.status_code == 201 else ""

    def update_task(self, remote_id: str, task) -> bool:
        if not self.access_token: return False
        body = {'title': task.title, 'status': 'completed' if task.status == 'completed' else 'notStarted'}
        r = requests.patch(f'https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{remote_id}', headers=self._headers(), json=body)
        return r.status_code == 200

    def delete_task(self, remote_id: str) -> bool:
        if not self.access_token: return False
        r = requests.delete(f'https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{remote_id}', headers=self._headers())
        return r.status_code == 204

    def get_lists(self) -> List[str]:
        if not self.access_token: return []
        r = requests.get('https://graph.microsoft.com/v1.0/me/todo/lists', headers=self._headers())
        if r.status_code != 200: return []
        return [l['displayName'] for l in r.json().get('value', [])]

    def create_list(self, name: str) -> bool:
        if not self.access_token: return False
        r = requests.post('https://graph.microsoft.com/v1.0/me/todo/lists', headers=self._headers(), json={'displayName': name})
        return r.status_code == 201
