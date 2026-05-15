#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title View Today's Tasks
# @raycast.mode fullOutput
# @raycast.packageName utask

# Optional parameters:
# @raycast.icon 📅
# @raycast.refreshTime 5m

# Documentation:
# @raycast.description Lists all tasks due today across all providers.
# @raycast.author aeon022

# Ensure the path to utask is correct
UTASK_BIN="$HOME/.local/bin/utask"

if [ ! -f "$UTASK_BIN" ]; then
  echo "Error: utask binary not found at $UTASK_BIN"
  exit 1
fi

# We don't have a direct 'today' CLI command yet, so we use list and grep or implement a small python snippet
# For now, let's use the list command as a base or suggest implementing a dedicated CLI command.
# Better: Let's output a nice list.
echo "📅 Today's Tasks:"
echo "----------------"
$UTASK_BIN today
