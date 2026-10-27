import keyring
import json
from typing import Any, Optional

SERVICE_NAME = "utask"

def _name(provider: str, key: str, label: Optional[str]) -> str:
    # Per account: "google:Private:token". Without a label this is the legacy shared key "google_token" (one account per provider).
    return f"{provider}:{label}:{key}" if label else f"{provider}_{key}"

def save_secret(provider: str, key: str, value: Any, label: Optional[str] = None):
    """Saves a secret value in the system keyring."""
    if not isinstance(value, str):
        value = json.dumps(value)
    keyring.set_password(SERVICE_NAME, _name(provider, key, label), value)

def load_secret(provider: str, key: str, is_json: bool = True, label: Optional[str] = None) -> Optional[Any]:
    """Loads a secret value from the system keyring."""
    value = keyring.get_password(SERVICE_NAME, _name(provider, key, label))
    if value and is_json:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

def delete_secret(provider: str, key: str, label: Optional[str] = None):
    """Deletes a secret value from the system keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, _name(provider, key, label))
    except keyring.errors.PasswordDeleteError:
        pass
