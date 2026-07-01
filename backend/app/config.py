"""Application configuration."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = PROJECT_ROOT / "app"
DATA_DIR = Path.home() / ".claudepilot"

# A separate DB for the test suite so tests never touch the user's real
# ~/.claudepilot/claudepilot.db (this env MUST be set before app.database is
# imported; tests/conftest.py does that at the very top). A real file is used
# rather than :memory: so multiple async connections in the same engine see
# the same tables.
if os.environ.get("CLAUDEPILOT_DB_URL"):
    DATABASE_URL = os.environ["CLAUDEPILOT_DB_URL"]
else:
    DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'claudepilot.db'}"

# Claude Code CLI stores one append-only jsonl per session here, organized by
# encoded project path: ~/<base>/projects/<encoded-path>/<session-id>.jsonl
CLAUDE_HISTORY_DIR = Path.home() / ".claude" / "projects"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
