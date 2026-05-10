import os
import json
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .config import load_tokens, save_tokens

SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_service():
    token_data = load_tokens("google")
    creds = Credentials.from_authorized_user_info(token_data, SCOPES) if token_data else None
    if not creds or not creds.valid:
        from pathlib import Path
        secret = Path.home() / ".config" / "tasksync" / "client_secret.json"
        if not secret.exists(): raise FileNotFoundError("client_secret.json missing")
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
        creds = flow.run_local_server(port=0)
        save_tokens("google", json.loads(creds.to_json()))
    return build('tasks', 'v1', credentials=creds)

def get_lists() -> List[str]:
    try:
        service = get_service()
        results = service.tasklists().list().execute()
        return [l['title'] for l in results.get('items', [])]
    except: return []

def get_tasks(list_name: str = "My Tasks") -> List[Dict[str, Any]]:
    """Holt Aufgaben einer Liste (Default: My Tasks oder erste Liste)."""
    try:
        service = get_service()
        lists = service.tasklists().list().execute().get('items', [])
        # Normalisierung: Google nennt die Standard-Liste oft "My Tasks"
        target_list = next((l for l in lists if l['title'] == list_name), None)
        if not target_list and lists: target_list = lists[0]
        if not target_list: return []
        
        results = service.tasks().list(tasklist=target_list['id']).execute()
        return results.get('items', [])
    except Exception as e:
        print(f"Google Task Fetch Error: {e}")
        return []

def create_task(title: str, list_name: str = "My Tasks") -> Optional[str]:
    try:
        service = get_service()
        lists = service.tasklists().list().execute().get('items', [])
        target_list = next((l for l in lists if l['title'] == list_name), None)
        if not target_list and lists: target_list = lists[0]
        list_id = target_list['id'] if target_list else "@default"
        
        result = service.tasks().insert(tasklist=list_id, body={'title': title}).execute()
        return result.get('id')
    except: return None
