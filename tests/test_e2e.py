import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, expect

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def running_server(command, directory, env, url, log_path):
    with log_path.open("w+") as log, subprocess.Popen(
        command, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT
    ) as server:
        try:
            deadline = time.monotonic() + 20
            while server.poll() is None and time.monotonic() < deadline:
                try:
                    with urlopen(url, timeout=1):
                        break
                except (URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                log.seek(0)
                pytest.fail(f"Server {url} did not start.\n{log.read()}")
            yield
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


@pytest.fixture
def app_url(tmp_path):
    api_port, frontend_port = free_port(), free_port()
    while frontend_port == api_port:
        frontend_port = free_port()
    api_url = f"http://127.0.0.1:{api_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    frontend = ROOT / "frontend"
    vite = frontend / "node_modules/vite/bin/vite.js"

    with (
        running_server(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(api_port)],
            ROOT, {**os.environ, "TASK_DB_PATH": str(tmp_path / "tasks.sqlite3")},
            f"{api_url}/api/tasks", tmp_path / "api.log",
        ),
        running_server(
            ["node", str(vite), "--host", "127.0.0.1", "--port", str(frontend_port), "--strictPort"],
            frontend, {**os.environ, "TASK_API_URL": api_url},
            f"{frontend_url}/api/tasks", tmp_path / "vite.log",
        ),
    ):
        yield frontend_url


def test_create_edit_filter_and_delete(page: Page, app_url: str):
    page.goto(app_url)
    expect(page.get_by_text("Add your first task to get started.")).to_be_visible()
    page.get_by_label("Task name").fill("Prepare report")
    page.get_by_label("Description").fill("Check the numbers")
    page.get_by_role("button", name="Add task").click()

    task = page.get_by_role("article").filter(has_text="Prepare report")
    expect(task.get_by_text("Check the numbers")).to_be_visible()
    expect(task.get_by_text("To do")).to_be_visible()

    task.get_by_role("button", name="Edit").click()
    page.get_by_label("Task name").fill("Send report")
    page.get_by_label("Task status").select_option("in_progress")
    page.get_by_role("button", name="Save changes").click()
    updated = page.get_by_role("article").filter(has_text="Send report")
    expect(updated.get_by_text("In progress")).to_be_visible()

    page.reload()
    expect(updated.get_by_text("In progress")).to_be_visible()
    status_filter = page.get_by_label("Filter by status")
    status_filter.select_option("done")
    expect(page.get_by_text("No tasks match this status.")).to_be_visible()
    status_filter.select_option("in_progress")
    expect(updated).to_be_visible()

    page.once("dialog", lambda dialog: dialog.accept())
    updated.get_by_role("button", name="Delete").click()
    expect(page.get_by_text("No tasks match this status.")).to_be_visible()
    page.reload()
    expect(page.get_by_text("Add your first task to get started.")).to_be_visible()
