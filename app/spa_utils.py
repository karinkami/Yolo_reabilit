"""Отдача собранного React-SPA (Vite → app/static/web-dist/)."""

from pathlib import Path

from flask import abort, current_app, send_from_directory


def send_web_spa():
    root = Path(current_app.static_folder or "") / "web-dist" / "index.html"
    if not root.is_file():
        abort(
            503,
            "Интерфейс не собран. В каталоге frontend выполните: npm install && npm run build",
        )
    resp = send_from_directory(current_app.static_folder, "web-dist/index.html")
    resp.headers["Cache-Control"] = "no-store"
    return resp
