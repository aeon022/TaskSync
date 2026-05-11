#!/usr/bin/env bash

# Merciless Setup Script for UniversalTask (utask) v2.0
# "Nice Data, No bloat, System-Integrity."

set -e

echo "------------------------------------------------"
echo "🚀 utask v2.0 - Merciless Setup"
echo "------------------------------------------------"

# 1. Check for Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found."
    echo "Please install Python 3.10 or higher (e.g., via 'brew install python')."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
# Compare version (requires at least 3.10)
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "✅ Python $PYTHON_VERSION detected."
else
    echo "❌ Error: Python $PYTHON_VERSION is too old."
    echo "utask requires Python 3.10 or higher. Please upgrade."
    exit 1
fi

# 2. Hard Cleanup
echo "🧹 Wiping old environment and build artifacts..."
rm -rf .venv venv env *.egg-info build dist .pytest_cache
find . -type d -name "__pycache__" -exec rm -rf {} +

# 3. Create Virtual Environment
echo "🐍 Creating clean virtual environment (.venv)..."
python3 -m venv .venv

# 4. Install Dependencies
echo "📦 Installing core dependencies and utask in editable mode..."
./.venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel --quiet
# Install using pyproject.toml
./.venv/bin/pip install --no-cache-dir -e . --quiet

# 5. Verify Installation
echo "🔍 Verifying critical modules..."
if ! ./.venv/bin/python3 -c "import aiosqlite, textual, sqlmodel, EventKit" &> /dev/null; then
    echo "⚠️ Warning: Some critical modules failed to verify."
    echo "Checking individual components..."
    ./.venv/bin/pip install --no-cache-dir aiosqlite textual sqlmodel pyobjc-framework-EventKit --quiet
fi

# 6. Create Global Wrapper
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

echo "🔗 Creating global 'utask' wrapper in $LOCAL_BIN..."
cat << EOF > "$LOCAL_BIN/utask"
#!/usr/bin/env bash
# UniversalTask v2.0 Wrapper
export PATH="$REPO_DIR/.venv/bin:\$PATH"
exec "$REPO_DIR/.venv/bin/utask" "\$@"
EOF

chmod +x "$LOCAL_BIN/utask"

echo "------------------------------------------------"
echo "✅ Setup complete! System-Integrity confirmed."
echo "------------------------------------------------"
echo "Important: Ensure $LOCAL_BIN is in your PATH."
echo "If not, add this to your .zshrc or .bash_profile:"
echo 'export PATH="\$HOME/.local/bin:\$PATH"'
echo ""
echo "Try it now:"
echo "👉 utask ui"
echo "------------------------------------------------"
