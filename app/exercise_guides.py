"""Инструкции по упражнениям: из таблицы exercise_guides с запасным текстом из кода."""

from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import joinedload

from app.exercise_guides_defaults import default_guide_for_key
from app.exercises import EXERCISES
from app.models import Exercise, ExerciseGuide


def _row_to_dict(g: ExerciseGuide) -> dict[str, Any]:
    return {
        "title": (g.title or "").strip(),
        "summary": (g.summary or "").strip(),
        "what_counts": (g.what_counts or "").strip(),
        "how_to": list(g.how_to or []),
        "mistakes": list(g.mistakes or []),
    }


def _merge_with_defaults(key: str, db: dict[str, Any] | None) -> dict[str, Any]:
    base = copy.deepcopy(default_guide_for_key(key))
    if not db:
        return base
    how_to = list(db.get("how_to") or [])
    mistakes = list(db.get("mistakes") or [])
    summary = (db.get("summary") or "").strip() or base["summary"]
    # Подъём вперёд: всегда актуальный текст из кода (в БД мог остаться устаревший «лицом»)
    if key == "forward_raise":
        return base
    return {
        "title": db.get("title") or base["title"],
        "summary": summary,
        "what_counts": db.get("what_counts") or base.get("what_counts", ""),
        "how_to": how_to if how_to else base["how_to"],
        "mistakes": mistakes if mistakes else base.get("mistakes", []),
    }


def get_guides() -> dict[str, dict[str, Any]]:
    """По ключу упражнения: title, summary, what_counts, how_to, mistakes."""
    rows = (
        ExerciseGuide.query.options(joinedload(ExerciseGuide.exercise))
        .join(Exercise)
        .order_by(Exercise.key)
        .all()
    )
    db_by_key: dict[str, dict[str, Any]] = {}
    for g in rows:
        ex = g.exercise
        if ex is None:
            continue
        db_by_key[ex.key] = _row_to_dict(g)

    out: dict[str, dict[str, Any]] = {}
    for key in EXERCISES:
        out[key] = _merge_with_defaults(key, db_by_key.get(key))
    return out


def get_guide_for_key(key: str) -> dict[str, Any] | None:
    if key not in EXERCISES:
        return None
    row = (
        ExerciseGuide.query.options(joinedload(ExerciseGuide.exercise))
        .join(Exercise)
        .filter(Exercise.key == key)
        .one_or_none()
    )
    db = _row_to_dict(row) if row else None
    return _merge_with_defaults(key, db)
