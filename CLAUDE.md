# ClaudePilot

## Project Context

ClaudePilot is a local web dashboard for Claude Code CLI. It does not replace the CLI; it wraps it with a modern UI, better conversation visualization, and native Chinese/English switching.

## Tech Stack

- **Backend**: Python 3.10, FastAPI, uvicorn, SQLAlchemy (async SQLite)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **Terminal**: xterm.js
- **Editor**: Monaco Editor
- **i18n**: react-i18next

## Development Rules

1. **Plan First**: for any non-trivial feature, write or update the plan before coding.
2. **TDD**: write tests before implementation for new behavior.
3. **Python Environment**: always use the `claudepilot` conda environment; never venv.
4. **Quality Gates**:
   - Backend: `ruff check .`, `mypy --strict app/`, `pytest`
   - Frontend: `npm run lint`, `npm run typecheck`, `npm run build`
5. **File Size**: keep files under 300 lines; break functions over 50 lines.
6. **Read Before Modifying**: one change at a time.

## Project Structure

```
backend/
  app/
    main.py              # FastAPI entry
    config.py            # App constants
    claude_driver/       # Claude CLI subprocess driver
    api/                 # FastAPI routers
    services/            # Business logic
    models.py            # SQLAlchemy models
    database.py          # Async DB setup
    websocket/           # WebSocket manager
    i18n/                # System prompt templates
  tests/
frontend/
  src/
    components/          # React components
    pages/               # Route-level pages
    stores/              # Zustand stores
    hooks/               # Custom hooks
    api/                 # HTTP client
    i18n/                # react-i18next config + translations
```

## Common Commands

```bash
# Backend
cd backend
conda run -n claudepilot uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
conda run -n claudepilot pytest
conda run -n claudepilot ruff check .
conda run -n claudepilot mypy --strict app/

# Frontend
cd frontend
npm run dev
npm run build
npm run typecheck
```

## Data Storage

All local data lives in `~/.claudepilot/`:

```
~/.claudepilot/
  claudepilot.db      # SQLite database
```
