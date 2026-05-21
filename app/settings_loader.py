import hashlib
import json
import os
from pathlib import Path
from typing import Any


def flask_safe_secret_key(raw: str | None) -> str:
    """Flask-Login подписывает remember-me cookie через .encode('latin-1') для ключа.
    Кириллица и прочий не-latin-1 в SECRET_KEY даёт UnicodeEncodeError — сводим к ASCII.
    """
    if not raw:
        return "dev-secret-change-me"
    try:
        raw.encode("latin-1")
        return raw
    except UnicodeEncodeError:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_app_settings() -> dict[str, Any]:
    root = project_root()
    for name in ("appsettings.json", "appsetting.json"):
        path = root / name
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def database_uri_from_settings(data: dict[str, Any]) -> str | None:
    if not data:
        return None
    cs = data.get("ConnectionStrings")
    if isinstance(cs, dict):
        v = cs.get("DefaultConnection")
        if v:
            s = str(v).strip()
            return s or None
    db = data.get("Database")
    if isinstance(db, dict):
        v = db.get("ConnectionString")
        if v:
            s = str(v).strip()
            return s or None
    v = data.get("SqlalchemyDatabaseUri")
    if v:
        s = str(v).strip()
        return s or None
    return None


def secret_key_from_settings(data: dict[str, Any]) -> str | None:
    for key in ("SecretKey", "SECRET_KEY"):
        v = data.get(key)
        if v:
            s = str(v).strip()
            return s or None
    return None


def resolve_database_uri() -> str:
    """
    Строка подключения к PostgreSQL: DATABASE_URI → appsettings.json.
    SQLite и запуск без настроек не поддерживаются.
    """
    json_settings = load_app_settings()
    uri = (
        (os.environ.get("DATABASE_URI") or "").strip()
        or database_uri_from_settings(json_settings)
        or ""
    )
    if not uri:
        raise RuntimeError(
            "Не задана строка подключения к PostgreSQL. "
            "Скопируйте appsettings.example.json → appsettings.json и укажите "
            "ConnectionStrings.DefaultConnection, либо задайте переменную DATABASE_URI. "
            "Инструкция: docs/ИНСТРУКЦИЯ_ПОДКЛЮЧЕНИЯ.md"
        )
    low = uri.lower()
    if low.startswith("sqlite"):
        raise RuntimeError(
            "SQLite отключён. Используйте PostgreSQL, например: "
            "postgresql+psycopg2://yolo_rehab:ПАРОЛЬ@localhost:5432/yolo_rehab"
        )
    if "postgresql" not in low and "+psycopg2" not in low:
        raise RuntimeError(
            "Ожидается URI PostgreSQL (postgresql+psycopg2://...). "
            "Проверьте appsettings.json или DATABASE_URI."
        )
    return uri
