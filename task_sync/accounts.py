"""Accounts: set up, check, re-authorize, remove. Used by the setup assistant in the TUI and by the CLI.

Secrets are stored per account label in the Keychain ("google:Private:token"). Older versions used one shared key per
provider ("google_token"); migrate_legacy_secrets() moves it to the first account of that provider.
"""
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .config import CONFIG_DIR, add_provider_config, load_provider_config, remove_provider_config
from .security import delete_secret, load_secret, save_secret

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/tasks"]
MS_SCOPES = ["Tasks.ReadWrite"]
OK, WARN, BAD = "ok", "warn", "bad"


# ---- migration ---------------------------------------------------------------------------------------------------
def migrate_legacy_secrets() -> List[str]:
    """Copy the old shared secrets to the first account of each provider. Returns what was moved (for a notice).
    Idempotent. With two accounts of one provider the old secret can belong to either: it goes to the first one and the
    second one shows 'sign in again' in the assistant, which is the safe outcome (never one token for two accounts)."""
    moved = []
    providers = load_provider_config()
    for kind, keys in (("google", ["token"]), ("microsoft", ["client_id", "tenant_id"])):
        labels = [p["label"] for p in providers if p["type"] == kind]
        if not labels:
            continue
        first = labels[0]
        for key in keys:
            legacy = load_secret(kind, key, is_json=(key == "token"))
            if legacy and not load_secret(kind, key, is_json=(key == "token"), label=first):
                save_secret(kind, key, legacy, label=first)
                moved.append(f"{kind}/{first}/{key}")
    return moved


# ---- status ------------------------------------------------------------------------------------------------------
def check_account(kind: str, label: str) -> Tuple[str, str]:
    """(state, text) for one configured account; tries the token, so 'ok' means it works."""
    try:
        if kind == "apple":
            from .api_apple import get_event_store, is_mac
            return (OK, "Reminders access granted") if is_mac() and get_event_store() else (BAD, "no access: allow utask in System Settings > Privacy > Reminders")
        if kind == "google":
            from .providers import get_provider
            inst = get_provider("google", label)
            if not inst or not inst.creds:
                return BAD, "not signed in"
            if inst.creds.expired and inst.creds.refresh_token:
                from google.auth.transport.requests import Request
                inst.creds.refresh(Request())
                inst._save_creds(inst.creds)
            return OK, "token works"
        if kind == "microsoft":
            from .providers import get_provider
            inst = get_provider("microsoft", label)
            if not inst or not inst.client_id:
                return BAD, "no client ID"
            if not inst.app.get_accounts():
                return BAD, "not signed in"
            return OK, "signed in"
    except Exception as e:  # e.g. invalid_grant
        text = str(e)
        return BAD, ("sign-in expired or revoked, sign in again" if "invalid_grant" in text else text[:100])
    return WARN, "unknown provider"


def list_accounts() -> List[Dict[str, str]]:
    """Configured accounts, without network access (fast): type, label."""
    return [dict(p) for p in load_provider_config()]


# ---- Google ------------------------------------------------------------------------------------------------------
def google_client_config(path_or_json: str = "", client_id: str = "", client_secret: str = "") -> dict:
    """Accepts the downloaded client_secret JSON (a path or its content) or an ID and a secret."""
    if client_id and client_secret:
        return {"installed": {"client_id": client_id, "client_secret": client_secret,
                              "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
                              "redirect_uris": ["http://localhost"]}}
    text = path_or_json.strip()
    if not text:
        raise ValueError("Give the client_secret.json file or a client ID and secret.")
    p = Path(text).expanduser()
    data = json.loads(p.read_text() if p.exists() else text)
    if "installed" not in data and "web" not in data:
        raise ValueError("This JSON is not a Google OAuth client file (it needs an 'installed' entry).")
    return data


def google_authorize(label: str, config: dict, open_browser: bool = True) -> str:
    """Runs the Google login in the browser (blocking, call it in a thread) and stores the token for this label."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_config(config, GOOGLE_SCOPES)
    creds = flow.run_local_server(port=0, open_browser=open_browser, timeout_seconds=240)
    save_secret("google", "token", json.loads(creds.to_json()), label=label)
    add_provider_config("google", label)
    return "Google Tasks authorized"


# ---- Microsoft ---------------------------------------------------------------------------------------------------
def microsoft_begin(label: str, client_id: str, tenant_id: str = "common"):
    """Starts the device-code login: returns (app, cache, flow). Show flow['user_code'] and flow['verification_uri']."""
    import msal
    cache = msal.SerializableTokenCache()
    app = msal.PublicClientApplication(client_id, authority=f"https://login.microsoftonline.com/{tenant_id or 'common'}", token_cache=cache)
    flow = app.initiate_device_flow(scopes=MS_SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(flow.get("error_description", "could not start the Microsoft sign-in"))
    return app, cache, flow


def microsoft_finish(label: str, client_id: str, tenant_id: str, app, cache, flow) -> str:
    """Waits for the code to be entered (blocking, call it in a thread), then stores the token cache for this label."""
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "sign-in failed"))
    save_secret("microsoft", "client_id", client_id, label=label)
    save_secret("microsoft", "tenant_id", tenant_id or "common", label=label)
    save_secret("microsoft", "cache", cache.serialize(), label=label)
    add_provider_config("microsoft", label)
    return "Microsoft To Do signed in"


# ---- Apple / remove ----------------------------------------------------------------------------------------------
def apple_add(label: str = "Apple") -> str:
    state, text = check_account("apple", label)
    if state != OK:
        raise RuntimeError(text)
    add_provider_config("apple", label)
    return text


def remove_account(kind: str, label: str) -> None:
    """Forget an account: its entry in the provider list and its Keychain secrets. Tasks already synced stay in the local database."""
    for key in ("token", "client_id", "tenant_id", "cache"):
        delete_secret(kind, key, label=label)
    remove_provider_config(kind, label)
