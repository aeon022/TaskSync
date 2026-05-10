#!/bin/bash
set -e

echo "------------------------------------------------"
echo "📦 TaskSync CLI Setup (EventKit Edition)"
echo "------------------------------------------------"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing/Updating dependencies..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install "sqlmodel>=0.0.30" "typer[all]>=0.15.0" "google-api-python-client" "google-auth-oauthlib" "msal" "requests" "textual>=0.50.0" 

# Der "Magische" Treiber für Apple Reminders (ohne die App zu öffnen)
echo "Installing macOS EventKit Bridge..."
./.venv/bin/pip install "pyobjc-framework-EventKit"

echo "Installing TaskSync in editable mode..."
./.venv/bin/pip install -e .

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
WRAPPER_SCRIPT="$BIN_DIR/utask"

cat << EOF > "$WRAPPER_SCRIPT"
#!/bin/bash
"$PWD/.venv/bin/python3" -m task_sync.main "\$@"
EOF
chmod +x "$WRAPPER_SCRIPT"

echo "------------------------------------------------"
echo "✅ Setup complete! Reminders App will now stay CLOSED."
echo "   Run: $WRAPPER_SCRIPT ui"
echo "------------------------------------------------"
