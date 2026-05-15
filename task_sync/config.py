import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_DIR = Path.home() / ".config" / "tasksync"
SHARED_PATH_POINTER = CONFIG_DIR / "shared_path.txt"

def ensure_config_dir():
    """Ensure the local configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt': # Set permissions on Unix-like systems
        os.chmod(CONFIG_DIR, 0o700)

def get_shared_dir() -> Path:
    """Returns the directory where shared configuration is stored."""
    ensure_config_dir()
    if SHARED_PATH_POINTER.exists():
        try:
            path_str = SHARED_PATH_POINTER.read_text().strip()
            if path_str:
                shared_path = Path(path_str).expanduser().absolute()
                shared_path.mkdir(parents=True, exist_ok=True)
                return shared_path
        except Exception:
            pass
    return CONFIG_DIR

def set_shared_dir(path: str):
    """Sets the pointer to the shared configuration directory."""
    ensure_config_dir()
    p = Path(path).expanduser().absolute()
    p.mkdir(parents=True, exist_ok=True)
    SHARED_PATH_POINTER.write_text(str(p))

def get_providers_file() -> Path:
    return get_shared_dir() / "providers.json"

def load_provider_config() -> List[Dict[str, str]]:
    """Loads the list of configured providers from the shared directory."""
    p_file = get_providers_file()
    if not p_file.exists():
        return []
    try:
        with open(p_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def add_provider_config(provider_type: str, label: str):
    """Adds or updates a provider in the shared configuration."""
    providers = load_provider_config()
    # Check if this exact combination exists
    for p in providers:
        if p["type"] == provider_type and p["label"] == label:
            return
    
    providers.append({"type": provider_type, "label": label})
    with open(get_providers_file(), "w") as f:
        json.dump(providers, f, indent=4)

# Legacy Token Logic (kept for compatibility if needed, but security.py is preferred)
TOKEN_FILE = CONFIG_DIR / "tokens.json"

def save_tokens(provider: str, tokens: Dict[str, Any]):
    ensure_config_dir()
    all_tokens = load_all_tokens()
    all_tokens[provider] = tokens
    with open(TOKEN_FILE, "w") as f:
        json.dump(all_tokens, f, indent=4)
    if os.name != 'nt':
        os.chmod(TOKEN_FILE, 0o600)

def load_tokens(provider: str) -> Optional[Dict[str, Any]]:
    return load_all_tokens().get(provider)

def load_all_tokens() -> Dict[str, Any]:
    if not TOKEN_FILE.exists():
        return {}
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
