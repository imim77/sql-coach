import asyncio
from pathlib import Path

from fastapi import FastAPI

from app.main import mount_frontend


def _get(application: FastAPI, path: str) -> tuple[int, bytes]:
    messages: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    asyncio.run(application(scope, receive, send))
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    return status, body


def test_mounted_frontend_serves_the_page_and_leaves_the_api(tmp_path: Path):
    (tmp_path / "index.html").write_text("<!doctype html><title>desk</title>", encoding="utf-8")
    application = FastAPI()

    @application.get("/api/health")
    def health():
        return {"ok": True}

    mount_frontend(application, tmp_path)

    status, body = _get(application, "/")
    assert status == 200
    assert b"desk" in body

    status, body = _get(application, "/api/health")
    assert status == 200
    assert b'"ok":true' in body or b'"ok": true' in body
