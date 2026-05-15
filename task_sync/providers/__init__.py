from typing import Optional
from .base import Provider
from .apple import AppleRemindersProvider
from .google import GoogleTasksProvider
from .microsoft import MicrosoftToDoProvider

def get_provider(provider_type: str, account_label: str) -> Optional[Provider]:
    """Factory to create a provider instance by type and label."""
    if provider_type == "apple":
        return AppleRemindersProvider(account_label=account_label)
    elif provider_type == "google":
        return GoogleTasksProvider(account_label=account_label)
    elif provider_type == "microsoft":
        return MicrosoftToDoProvider(account_label=account_label)
    return None
