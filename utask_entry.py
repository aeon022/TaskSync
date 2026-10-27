"""PyInstaller entry point: the package must be imported as a package (main.py uses relative imports)."""
from task_sync.main import app

if __name__ == "__main__":
    app()
