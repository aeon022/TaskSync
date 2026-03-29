from typing import List, Optional
from datetime import datetime
import subprocess
import json
from .base import RemoteTask, Provider

class AppleRemindersProvider:
    name = "apple"

    def __init__(self, list_name: Optional[str] = None):
        self._list_name = list_name

    def _run_applescript(self, script: str) -> str:
        """Run an AppleScript and return the output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return ""

    @property
    def list_name(self) -> str:
        if self._list_name:
            return self._list_name
        
        # Try to find ALL list names
        names_raw = self._run_applescript('tell application "Reminders" to get name of every list')
        if names_raw:
            list_names = [n.strip() for n in names_raw.split(",")]
            if "Reminders" in list_names:
                self._list_name = "Reminders"
            elif "Erinnerungen" in list_names:
                self._list_name = "Erinnerungen"
            elif list_names:
                self._list_name = list_names[0]
        
        if not self._list_name:
            self._list_name = "Reminders"
            
        return self._list_name

    def get_lists(self) -> List[str]:
        names_raw = self._run_applescript('tell application "Reminders" to get name of every list')
        if names_raw:
            return [n.strip() for n in names_raw.split(",")]
        return []

    def get_tasks(self) -> List[RemoteTask]:
        """Fetch tasks using AppleScript."""
        target = self.list_name
        script = f'''
        set output to ""
        tell application "Reminders"
            try
                set myList to list "{target}"
                set theTasks to reminders of myList
                repeat with t in theTasks
                    set tid to id of t
                    set tname to name of t
                    set tdone to completed of t
                    set tmod to modification date of t
                    
                    set yr to year of tmod as integer
                    set mo to month of tmod as integer
                    set dy to day of tmod as integer
                    set hr to hours of tmod
                    set mn to minutes of tmod
                    set sc to seconds of tmod
                    set dateStr to (yr as string) & "-" & (mo as string) & "-" & (dy as string) & "T" & (hr as string) & ":" & (mn as string) & ":" & (sc as string)
                    
                    set output to output & tid & "|" & tname & "|" & (tdone as string) & "|" & dateStr & "\n"
                end repeat
            on error
                return ""
            end try
        end tell
        return output
        '''
        raw_output = self._run_applescript(script)
        if not raw_output:
            return []

        remote_tasks = []
        for line in raw_output.split("\n"):
            if not line: continue
            parts = line.split("|")
            if len(parts) < 4: continue
            
            status = "completed" if parts[2].lower() == "true" else "needsAction"
            try:
                mod_date = datetime.fromisoformat(parts[3])
            except:
                mod_date = datetime.utcnow()

            remote_tasks.append(RemoteTask(
                remote_id=parts[0],
                title=parts[1],
                status=status,
                last_modified=mod_date
            ))
        return remote_tasks

    def create_task(self, task) -> str:
        """Create a new reminder."""
        target = self.list_name
        title_esc = task.title.replace('"', '\\"')
        script = f'''
        tell application "Reminders"
            if not (exists list "{target}") then
                make new list with properties {{name:"{target}"}}
            end if
            set myList to list "{target}"
            tell myList
                set newRem to make new reminder with properties {{name:"{title_esc}"}}
                return id of newRem
            end tell
        end tell
        '''
        return self._run_applescript(script)

    def update_task(self, remote_id: str, task) -> bool:
        completed = "true" if task.status == "completed" else "false"
        # Escape quotes in title
        title_esc = task.title.replace('"', '\\"')
        script = f'''
        tell application "Reminders"
            try
                set t to reminder id "{remote_id}"
                set name of t to "{title_esc}"
                set completed of t to {completed}
                return "true"
            on error
                return "false"
            end try
        end tell
        '''
        return self._run_applescript(script) == "true"

    def delete_task(self, remote_id: str) -> bool:
        script = f'''
        tell application "Reminders"
            try
                delete reminder id "{remote_id}"
                return "true"
            on error
                return "false"
            end try
        end tell
        '''
        return self._run_applescript(script) == "true"

    # List Operations
    def create_list(self, name: str) -> bool:
        script = f'''
        tell application "Reminders"
            try
                if not (exists list "{name}") then
                    make new list with properties {{name:"{name}"}}
                    return "true"
                else
                    return "exists"
                end if
            on error
                return "false"
            end try
        end tell
        '''
        return self._run_applescript(script) in ["true", "exists"]

    def delete_list(self, name: str) -> bool:
        script = f'''
        tell application "Reminders"
            try
                delete list "{name}"
                return "true"
            on error
                return "false"
            end try
        end tell
        '''
        return self._run_applescript(script) == "true"

    def rename_list(self, old_name: str, new_name: str) -> bool:
        script = f'''
        tell application "Reminders"
            try
                set name of list "{old_name}" to "{new_name}"
                return "true"
            on error
                return "false"
            end try
        end tell
        '''
        return self._run_applescript(script) == "true"
