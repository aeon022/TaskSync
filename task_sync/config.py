import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path.home() / ".config" / "tasksync"
TOKEN_FILE = CONFIG_DIR / "tokens.json"

def ensure_config_dir():
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Set permissions to 700 for security
    os.chmod(CONFIG_DIR, 0o700)

def save_tokens(provider: str, tokens: Dict[str, Any]):
    """Save OAuth tokens for a specific provider."""
    ensure_config_dir()
    
    all_tokens = load_all_tokens()
    all_tokens[provider] = tokens
    
    with open(TOKEN_FILE, "w") as f:
        json.dump(all_tokens, f, indent=4)
    
    # Set file permissions to 600 for security
    os.chmod(TOKEN_FILE, 0o600)

def load_tokens(provider: str) -> Optional[Dict[str, Any]]:
    """Load OAuth tokens for a specific provider."""
    all_tokens = load_all_tokens()
    return all_tokens.get(provider)

def load_all_tokens() -> Dict[str, Any]:
    """Load all stored tokens from the config file."""
    if not TOKEN_FILE.exists():
        return {}
    
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def delete_tokens(provider: str):
    """Delete stored tokens for a specific provider."""
    all_tokens = load_all_tokens()
    if provider in all_tokens:
        del all_tokens[provider]
        with open(TOKEN_FILE, "w") as f:
            json.dump(all_tokens, f, indent=4)
