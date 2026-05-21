"""Отображение истории подходов: сторона и прогресс 1/2 для связок."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.datetime_util import utc_iso_z
from app.exercise_kinds import is_dual_arm_exercise
from app.models import TrainingSession
from app.session_aggregate import collapse_training_sessions
from app.side_labels import side_label_full


def _minute_key(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.replace(second=0, microsecond=0).isoformat()


def _infer_bundle_parts(sessions: list[TrainingSession]) -> dict[int, tuple[int, int]]:
    """Для старых записей без bundle_part: пары подходов с одним упражнением в одну минуту."""
    by_key: dict[tuple[str, str], list[TrainingSession]] = defaultdict(list)
    for s in sessions:
        if is_dual_arm_exercise(s.exercise_key):
            continue
        if getattr(s, "bundle_part", None) and getattr(s, "bundle_size", None):
            continue
        by_key[(s.exercise_key, _minute_key(s.completed_at))].append(s)

    out: dict[int, tuple[int, int]] = {}
    for group in by_key.values():
        if len(group) != 2:
            continue
        ordered = sorted(group, key=lambda x: (x.completed_at or datetime.min, x.id))
        out[ordered[0].id] = (1, 2)
        out[ordered[1].id] = (2, 2)
    return out


def serialize_training_session(
    s: TrainingSession,
    *,
    inferred: dict[int, tuple[int, int]] | None = None,
) -> dict[str, Any]:
    part = getattr(s, "bundle_part", None)
    total = getattr(s, "bundle_size", None)
    side = getattr(s, "side", None)

    if (part is None or total is None) and inferred and s.id in inferred:
        part, total = inferred[s.id]

    side_label = ""
    if side in ("left", "right"):
        side_label = side_label_full(side, s.exercise_key)

    bundle_progress_label = ""
    if total and int(total) > 1 and part:
        bundle_progress_label = f"{int(part)}/{int(total)}"

    exercise_display = s.exercise_label or s.exercise_key
    is_half = bool(bundle_progress_label and part and total and int(part) < int(total))
    if side_label and bundle_progress_label and is_half:
        exercise_display = f"{exercise_display} — {side_label}"

    score_percent = int(s.score_percent or 0)
    summary = s.correctness_summary or ""
    if is_half and not summary.startswith("Подход остановлен"):
        score_percent = 50
        summary = f"Цель не достигнута ({bundle_progress_label})"

    return {
        "id": s.id,
        "completed_at": utc_iso_z(s.completed_at),
        "exercise_key": s.exercise_key,
        "exercise_label": s.exercise_label,
        "exercise_display": exercise_display,
        "side": side,
        "side_label": side_label,
        "bundle_part": int(part) if part else None,
        "bundle_size": int(total) if total else None,
        "bundle_progress_label": bundle_progress_label,
        "reps_completed": s.reps_completed,
        "target_reps": s.target_reps,
        "score_percent": score_percent,
        "correctness_summary": summary,
        "is_half_of_bundle": is_half,
    }


def stats_score_eligible(ser: dict[str, Any]) -> bool:
    """Неполная связка (1/2): в истории 50%, в среднюю оценку не входит (иначе 75% при 2/2)."""
    return not bool(ser.get("is_half_of_bundle"))


def history_sessions_for_patient(sessions: list[TrainingSession]) -> list[dict[str, Any]]:
    asc = sorted(sessions, key=lambda x: (x.completed_at or datetime.min, x.id))
    inferred = _infer_bundle_parts(asc)
    collapsed = collapse_training_sessions(sessions)
    desc = sorted(collapsed, key=lambda x: (x.completed_at or datetime.min, x.id), reverse=True)
    return [serialize_training_session(s, inferred=inferred) for s in desc]
