#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Add Task
# @raycast.mode silent
# @raycast.packageName utask

# Optional parameters:
# @raycast.icon 🚀
# @raycast.argument1 { "type": "text", "placeholder": "Task title (e.g. Meeting tomorrow 10am)" }

# Documentation:
# @raycast.description Adds a new task to utask using NLP date parsing.
# @raycast.author aeon022

# Ensure the path to utask is correct
UTASK_BIN="$HOME/.local/bin/utask"

if [ ! -f "$UTASK_BIN" ]; then
  echo "Error: utask binary not found at $UTASK_BIN"
  exit 1
fi

# Execute add command
RESULT=$($UTASK_BIN add "$1" 2>&1)

if [ $? -eq 0 ]; then
  echo "Task added: $1"
else
  echo "Failed to add task: $RESULT"
fi
