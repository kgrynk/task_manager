# Task Manager

A local app for managing tasks. Each task has a name, an optional description, and one of three statuses: **To do**, **In progress**, or **Done**. You can add, edit, delete, and filter tasks. SQLite stores your tasks across application restarts.

## Run locally

You'll need Python 3.11+ with SQLite 3.35+, Node.js 22+, and pnpm. Run these commands from the project directory in Bash.

Start the API in the first terminal.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Start the frontend in a second terminal.

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend dev
```

Open the [app](http://127.0.0.1:5173). Use the [OpenAPI docs](http://127.0.0.1:8000/docs) to explore request formats and try the endpoints. Vite forwards requests under `/api` to FastAPI. The first API startup creates `backend/tasks.sqlite3`. Set `TASK_DB_PATH` to use a different database path.

## API

| Method | Path | Action |
| --- | --- | --- |
| GET | `/api/tasks` | List tasks with an optional `status` filter |
| POST | `/api/tasks` | Create a task |
| GET | `/api/tasks/{id}` | Get a task |
| PUT | `/api/tasks/{id}` | Replace a task's details |
| DELETE | `/api/tasks/{id}` | Delete a task |

Example request body for POST or PUT

```json
{"title": "Prepare report", "description": "Fill in the missing data", "status": "in_progress"}
```

The API accepts `todo`, `in_progress`, and `done` as status values.

## Tests and build

Install the frontend dependencies first, then run these commands from the project directory. The E2E test starts its own servers and uses a temporary database, so you can leave a running instance of the app open.

```bash
source .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python -m pytest tests/test_api.py
python -m pytest tests/test_e2e.py
pnpm --dir frontend build
```
