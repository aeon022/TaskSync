import platform
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

def is_mac() -> bool:
    return platform.system() == "Darwin"

def get_event_store():
    try:
        from EventKit import EKEventStore
        store = EKEventStore.alloc().init()
        return store
    except ImportError:
        return None

def update_task(remote_id: str, title: Optional[str] = None, completed: Optional[bool] = None) -> bool:
    store = get_event_store()
    if not store: return False
    
    reminder = store.calendarItemWithIdentifier_(remote_id)
    if not reminder: return False
    
    if title is not None:
        reminder.setTitle_(title)
    if completed is not None:
        reminder.setCompleted_(completed)
        
    success, error = store.saveReminder_commit_error_(reminder, True, None)
    return bool(success)

def get_lists() -> List[str]:
    """Holt alle Listen-Namen von Apple Reminders."""
    if not is_mac(): return []
    from EventKit import EKEntityTypeReminder
    store = get_event_store()
    if not store: return []
    calendars = store.calendarsForEntityType_(EKEntityTypeReminder)
    return [cal.title() for cal in calendars]

def get_tasks(list_name: str = "Reminders") -> List[Dict[str, Any]]:
    """Holt Aufgaben einer Liste ohne die App zu öffnen."""
    if not is_mac(): return []
    from EventKit import EKEntityTypeReminder
    store = get_event_store()
    if not store: return []

    calendars = store.calendarsForEntityType_(EKEntityTypeReminder)
    target_cal = next((c for c in calendars if c.title() == list_name or (list_name == "Reminders" and c.title() == "Erinnerungen")), None)
    if not target_cal: return []

    predicate = store.predicateForRemindersInCalendars_([target_cal])
    reminders = []
    import threading
    event = threading.Event()
    def callback(items):
        if items:
            for r in items:
                reminders.append({
                    "id": r.calendarItemExternalIdentifier(),
                    "title": r.title(),
                    "completed": r.isCompleted(),
                    "list_name": list_name
                })
        event.set()
    store.fetchRemindersMatchingPredicate_completion_(predicate, callback)
    event.wait(timeout=5)
    return reminders

def delete_list(name: str) -> bool:
    """Löscht eine Liste in Apple Erinnerungen."""
    if not is_mac(): return False
    from EventKit import EKEntityTypeReminder
    store = get_event_store()
    if not store: return False
    calendars = store.calendarsForEntityType_(EKEntityTypeReminder)
    target_cal = next((c for c in calendars if c.title() == name), None)
    if not target_cal: return False
    success, error = store.removeCalendar_commit_error_(target_cal, True, None)
    return bool(success)
