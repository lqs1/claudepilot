# ClaudePilot

A modern web-based scheduler and visualizer for [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code).

## Features

- **Project Management**: manage multiple local projects in one place.
- **Modern Chat UI**: real-time streaming, Markdown rendering, tool call cards.
- **Terminal**: embedded PTY terminal powered by xterm.js.
- **File Editor**: file tree + Monaco Editor.
- **History & Recovery**: SQLite persistence and session resumption.
- **Chinese / English Switching**: UI language, system prompt language, and code/doc language preference.

## Tech Stack

- Backend: Python 3.10 + FastAPI + uvicorn + SQLAlchemy (async SQLite)
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui

## Development

### Backend

```bash
cd backend
conda env list | grep claudepilot || conda create -n claudepilot python=3.10 -y
conda run -n claudepilot pip install -r requirements.txt
conda run -n claudepilot uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## License

MIT
