import msal
import requests
from typing import List, Dict, Any, Optional
from .config import load_tokens, save_tokens

# Constants for Microsoft Graph
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Tasks.ReadWrite"]
CLIENT_ID_FILE = "ms_client_id.txt" # Should be in ~/.config/tasksync/

def get_access_token():
    """Gets a valid access token for Microsoft Graph."""
    from pathlib import Path
    config_dir = Path.home() / ".config" / "tasksync"
    client_id_path = config_dir / CLIENT_ID_FILE
    
    if not client_id_path.exists():
        raise FileNotFoundError(f"Microsoft Client ID not found at {client_id_path}")
    
    with open(client_id_path, "r") as f:
        client_id = f.read().strip()

    app = msal.PublicClientApplication(client_id, authority=AUTHORITY)
    
    token_data = load_tokens("microsoft")
    accounts = app.get_accounts()
    
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    
    if not result:
        # Fallback to interactive login
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise Exception("Could not initiate device flow")
            
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
        
    if "access_token" in result:
        # Save tokens for next time (MSAL handles persistence internally, but we bridge it)
        # In a real app, MSAL's TokenCache should be serialized.
        return result["access_token"]
    else:
        raise Exception(f"Could not acquire token: {result.get('error_description')}")

def get_tasks() -> List[Dict[str, Any]]:
    """Fetch all tasks from the default To Do list."""
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get default task list ID first
        r_lists = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=headers)
        r_lists.raise_for_status()
        lists = r_lists.json().get("value", [])
        
        if not lists:
            return []
            
        # Use the first list (usually 'Tasks')
        list_id = lists[0]["id"]
        
        r_tasks = requests.get(f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks", headers=headers)
        r_tasks.raise_for_status()
        return r_tasks.json().get("value", [])
    except Exception as e:
        print(f"Error fetching MS tasks: {e}")
        return []

def create_task(title: str) -> Optional[str]:
    """Create a new task in the default To Do list."""
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Get default task list ID
        r_lists = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=headers)
        r_lists.raise_for_status()
        list_id = r_lists.json()["value"][0]["id"]
        
        payload = {"title": title}
        r_new = requests.post(f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks", headers=headers, json=payload)
        r_new.raise_for_status()
        return r_new.json().get("id")
    except Exception as e:
        print(f"Error creating MS task: {e}")
        return None
