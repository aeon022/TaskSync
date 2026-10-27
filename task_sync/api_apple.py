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

def update_task(remote_id: str, title: Optional[str] = None, completed: Optional[bool] = None, due=None, set_due: bool = False) -> bool:
    store = get_event_store()
    if not store: return False
    
    reminder = store.calendarItemWithIdentifier_(remote_id)
    if not reminder: return False
    
    if title is not None:
        reminder.setTitle_(title)
    if completed is not None:
        reminder.setCompleted_(completed)
    if set_due and _due(reminder.dueDateComponents()) != due:  # same day: keep the reminder's time of day
        reminder.setDueDateComponents_(_components(due))

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

def _components(due):
    """(y, m, d) or None -> NSDateComponents (date only) or None to clear the due date."""
    if not due: return None
    from Foundation import NSDateComponents
    c = NSDateComponents.alloc().init()
    c.setYear_(due[0]); c.setMonth_(due[1]); c.setDay_(due[2])
    return c

def _due(comps):
    """EKReminder.dueDateComponents -> (y, m, d) or None. Missing parts come back as a huge sentinel."""
    if comps is None: return None
    y, m, d = comps.year(), comps.month(), comps.day()
    return (y, m, d) if 1970 < y < 3000 and 1 <= m <= 12 and 1 <= d <= 31 else None

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
                    "due": _due(r.dueDateComponents()),
                    "list_name": list_name
                })
        event.set()
    store.fetchRemindersMatchingPredicate_completion_(predicate, callback)
    event.wait(timeout=5)
    return reminders

def create_task(title: str, list_name: str) -> Optional[str]:
    """Erstellt eine neue Aufgabe in Apple Erinnerungen."""
    if not is_mac(): return None
    from EventKit import EKReminder, EKEntityTypeReminder
    store = get_event_store()
    if not store: return None

    calendars = store.calendarsForEntityType_(EKEntityTypeReminder)
    target_cal = next((c for c in calendars if c.title() == list_name or (list_name == "Reminders" and c.title() == "Erinnerungen")), None)
    if not target_cal: return None

    reminder = EKReminder.reminderWithEventStore_(store)
    reminder.setTitle_(title)
    reminder.setCalendar_(target_cal)
    
    success, error = store.saveReminder_commit_error_(reminder, True, None)
    if success:
        return reminder.calendarItemExternalIdentifier()
    return None

def create_list(name: str) -> bool:
    """Erstellt eine neue Liste (Calendar) in Apple Erinnerungen."""
    if not is_mac(): return False
    from EventKit import EKCalendar, EKEntityTypeReminder
    store = get_event_store()
    if not store: return False

    # Existiert die Liste bereits?
    existing = get_lists()
    if name in existing: return True

    # Neue Liste erstellen
    new_cal = EKCalendar.calendarForEntityType_eventStore_(EKEntityTypeReminder, store)
    new_cal.setTitle_(name)
    
    # Einen passenden Speicherort (Source) finden
    # Wir nehmen die Source des Standard-Kalenders oder die erste iCloud/Local Source
    default_cal = store.defaultCalendarForNewReminders()
    if default_cal:
        new_cal.setSource_(default_cal.source())
    else:
        # Fallback: Suche nach einer lokalen oder iCloud Source
        from EventKit import EKSourceTypeLocal, EKSourceTypeICloud
        sources = store.sources()
        target_source = next((s for s in sources if s.sourceType() == EKSourceTypeICloud), None)
        if not target_source:
            target_source = next((s for s in sources if s.sourceType() == EKSourceTypeLocal), None)
        if not target_source: return False
        new_cal.setSource_(target_source)

    success, error = store.saveCalendar_commit_error_(new_cal, True, None)
    return bool(success)

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
