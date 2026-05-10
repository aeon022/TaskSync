import keyring
import json
from typing import Any, Dict, Optional

SERVICE_NAME = "utask"

def save_secret(provider: str, key: str, value: Any):
    """Saves a secret value in the system keyring."""
    # Convert value to JSON if it's not a string
    if not isinstance(value, str):
        value = json.dumps(value)
    keyring.set_password(SERVICE_NAME, f"{provider}_{key}", value)

def load_secret(provider: str, key: str, is_json: bool = True) -> Optional[Any]:
    """Loads a secret value from the system keyring."""
    value = keyring.get_password(SERVICE_NAME, f"{provider}_{key}")
    if value and is_json:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value

def delete_secret(provider: str, key: str):
    """Deletes a secret value from the system keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, f"{provider}_{key}")
    except keyring.errors.PasswordDeleteError:
        pass
