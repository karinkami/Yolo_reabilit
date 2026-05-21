"""Создать таблицы приложения и начальные данные (сид) без запуска веб-сервера.

Запуск из корня проекта (с активированным venv):

    python scripts/init_database.py

То же самое делает первый запуск ``python run.py`` — см. ``app/__init__.py`` (create_app).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db
from app.models import Exercise, User


def _mask_db_uri(uri: str) -> str:
    if not uri:
        return "(не задано)"
    return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1****\3", uri, count=1)


def main() -> int:
    app = create_app()
    with app.app_context():
        uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
        exercises_n = Exercise.query.count()
        doctors_n = User.query.filter_by(role="doctor").count()

    print()
    print("=== YOLO Reabilit — инициализация БД ===")
    print(f"Подключение: {_mask_db_uri(uri)}")
    if "postgresql" in uri:
        print("Тип: PostgreSQL (пустая база yolo_rehab должна быть создана в pgAdmin)")
    else:
        print("Тип: не PostgreSQL — проверьте appsettings.json")
    print()
    print("Выполнено:")
    print("  • db.create_all() — таблицы по models.py")
    print("  • schema_patch — недостающие колонки (если БД старая)")
    print("  • seed_exercises() — каталог упражнений")
    print("  • seed_demo_doctor() — демо-врач (если врачей ещё не было)")
    print()
    print(f"Упражнений в каталоге: {exercises_n}")
    print(f"Учётных записей врача: {doctors_n}")
    print()
    print("Демо-врач (если только что создан): doctor@clinic.local / doctor123")
    print("Пациенты — через регистрацию на сайте.")
    print()
    print("Готово. Можно запускать: python run.py")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
