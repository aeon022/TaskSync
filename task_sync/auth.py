import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from .security import save_secret

SCOPES = ['https://www.googleapis.com/auth/tasks']

def auth_google(client_secrets_json: str):
    """Performs OAuth2 flow using raw JSON content."""
    secrets_data = json.loads(client_secrets_json)
    return _run_google_flow(secrets_data)

def auth_google_manual(client_id: str, client_secret: str):
    """Performs OAuth2 flow using individual ID and Secret."""
    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }
    return _run_google_flow(config)

def _run_google_flow(config: dict):
    """Common logic to run the Google OAuth flow."""
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    creds = flow.run_local_server(port=0)
    save_secret("google", "token", json.loads(creds.to_json()))
    return "Google Tasks erfolgreich autorisiert!"

def auth_microsoft(client_id: str, tenant_id: str = "common"):
    """
    Saves Microsoft credentials to keyring.
    """
    save_secret("microsoft", "client_id", client_id)
    save_secret("microsoft", "tenant_id", tenant_id)
    return "Microsoft Credentials gespeichert! Bitte starte 'utask sync' für den ersten Login."
