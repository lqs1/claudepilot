"""Application configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = PROJECT_ROOT / "app"
DATA_DIR = Path.home() / ".claudepilot"
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'claudepilot.db'}"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
