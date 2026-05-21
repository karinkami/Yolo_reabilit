"""Сгенерировать scripts/exercise_guides_schema_and_data.sql из exercise_guides_defaults.py.

Запуск из корня проекта (с активированным venv):

    python scripts/export_exercise_guides_sql.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.exercise_guides_defaults import GUIDES_BY_KEY

OUT = ROOT / "scripts" / "exercise_guides_schema_and_data.sql"


def _sql_json_array(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def main() -> None:
    parts = [
        "-- Инструкции к упражнениям в PostgreSQL.",
        "-- Синхронизировано с app/exercise_guides_defaults.py",
        "-- Пересоздать: python scripts/export_exercise_guides_sql.py",
        "--",
        "-- Запускайте после сида упражнений (run.py или init_database.py).",
        "",
        "BEGIN;",
        "",
        "CREATE TABLE IF NOT EXISTS exercise_guides (",
        "  id SERIAL PRIMARY KEY,",
        "  exercise_id INTEGER NOT NULL UNIQUE REFERENCES exercises (id) ON DELETE CASCADE,",
        "  title VARCHAR(300) NOT NULL,",
        "  summary TEXT NOT NULL DEFAULT '',",
        "  what_counts TEXT NOT NULL DEFAULT '',",
        "  how_to JSONB NOT NULL DEFAULT '[]'::jsonb,",
        "  mistakes JSONB NOT NULL DEFAULT '[]'::jsonb",
        ");",
        "",
    ]

    for key, g in GUIDES_BY_KEY.items():
        title = g["title"].replace("'", "''")
        summary = g["summary"].replace("'", "''")
        what_counts = (g.get("what_counts") or "").replace("'", "''")
        how_to = _sql_json_array(list(g["how_to"]))
        mistakes = _sql_json_array(list(g.get("mistakes") or []))

        parts.extend(
            [
                f"-- {key}",
                "INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)",
                "SELECT e.id,",
                f"  '{title}',",
                f"  '{summary}',",
                f"  '{what_counts}',",
                f"  '{how_to}'::jsonb,",
                f"  '{mistakes}'::jsonb",
                f"FROM exercises e WHERE e.key = '{key}'",
                "ON CONFLICT (exercise_id) DO UPDATE SET",
                "  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,",
                "  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;",
                "",
            ]
        )

    parts.append("COMMIT;")
    parts.append("")

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Записано: {OUT} ({len(GUIDES_BY_KEY)} упражнений)")


if __name__ == "__main__":
    main()
