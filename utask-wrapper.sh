#!/bin/bash

# utask-wrapper.sh
# Globaler Entrypoint für Raycast, Alfred oder Apple Shortcuts.
# Ermöglicht schnelles Hinzufügen von Tasks ohne Terminal-Fokus.

# Pfad zur utask Binary oder zum Python-Script anpassen
UTASK_CMD="python3 -m task_sync.main"

if [ -z "$1" ]; then
    echo "Benutzung: utask-wrapper.sh 'Aufgaben Titel morgen 10:00'"
    exit 1
fi

# Task hinzufügen via CLI
$UTASK_CMD add "$1"

# Optionale macOS Notification (AppleScript)
osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "Task hinzugefügt: $1" "utask"
