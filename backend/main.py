import os
import sqlite3
from contextlib import asynccontextmanager, closing
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as PathParam, Response
from pydantic import BaseModel, StringConstraints


class Status(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskInput(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    description: Annotated[str, StringConstraints(max_length=1000)] = ""
    status: Status = Status.TODO


class Task(TaskInput):
    id: int


TaskId = Annotated[int, PathParam(ge=1, le=2**63 - 1)]
DEFAULT_DB = Path(__file__).with_name("tasks.sqlite3")


def create_app(database: str | Path | None = None) -> FastAPI:
    db_path = Path(database or os.environ.get("TASK_DB_PATH") or DEFAULT_DB)

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'done'))
                )
            """)
        yield

    app = FastAPI(title="Task Manager API", lifespan=lifespan)

    def require_task(row: sqlite3.Row | None) -> dict:
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return dict(row)

    @app.get("/api/tasks", response_model=list[Task])
    def list_tasks(status: Status | None = None):
        with closing(connect()) as db:
            if status is None:
                rows = db.execute("SELECT * FROM tasks ORDER BY id DESC")
            else:
                rows = db.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,)
                )
            return [dict(row) for row in rows]

    @app.post("/api/tasks", response_model=Task, status_code=201)
    def create_task(task: TaskInput):
        with closing(connect()) as db, db:
            cursor = db.execute(
                "INSERT INTO tasks (title, description, status) VALUES (:title, :description, :status)",
                task.model_dump(),
            )
            return Task(id=cursor.lastrowid, **task.model_dump())

    @app.get("/api/tasks/{task_id}", response_model=Task)
    def get_task(task_id: TaskId):
        with closing(connect()) as db:
            return require_task(db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

    @app.put("/api/tasks/{task_id}", response_model=Task)
    def update_task(task_id: TaskId, task: TaskInput):
        with closing(connect()) as db, db:
            result = db.execute(
                """UPDATE tasks
                   SET title = :title, description = :description, status = :status
                   WHERE id = :id RETURNING *""",
                {"id": task_id, **task.model_dump()},
            ).fetchone()
            return require_task(result)

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def delete_task(task_id: TaskId):
        with closing(connect()) as db, db:
            result = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Task not found.")
        return Response(status_code=204)

    return app


app = create_app()
