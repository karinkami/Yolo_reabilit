"""Одна запись истории на связку (левая+правая), подсчёт сторон для sync."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.models import TrainingSession


def _minute_key(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.replace(second=0, microsecond=0).isoformat()


def _bundle_rank(s: TrainingSession) -> tuple[int, datetime, int]:
    part = int(getattr(s, "bundle_part", None) or 0)
    total = int(getattr(s, "bundle_size", None) or 0)
    if total > 1 and part == 0:
        part = 1
    at = s.completed_at or datetime.min
    return (part, at, int(s.id or 0))


def _pick_representative(group: list[TrainingSession]) -> TrainingSession:
    return max(group, key=_bundle_rank)


def collapse_training_sessions(sessions: list[TrainingSession]) -> list[TrainingSession]:
    """
    Одна строка на попытку упражнения: для связки — запись с максимальным bundle_part.
    """
    by_gid: dict[str, list[TrainingSession]] = defaultdict(list)
    legacy_bundle: dict[tuple[str, str], list[TrainingSession]] = defaultdict(list)
    standalone: list[TrainingSession] = []

    for s in sessions:
        gid = getattr(s, "assignment_group_id", None)
        total = int(getattr(s, "bundle_size", None) or 0)
        if gid and total > 1:
            by_gid[str(gid)].append(s)
        elif total > 1:
            legacy_bundle[(s.exercise_key, _minute_key(s.completed_at))].append(s)
        else:
            standalone.append(s)

    out: list[TrainingSession] = list(standalone)
    for group in by_gid.values():
        out.append(_pick_representative(group))
    for group in legacy_bundle.values():
        out.append(_pick_representative(group))
    return out


def successful_sides_count(
    patient_id: int,
    exercise_key: str,
    since: datetime,
    target_reps: int,
) -> int:
    """Число выполненных сторон (для связки — по bundle_part, не по числу строк)."""
    rows = (
        TrainingSession.query.filter(
            TrainingSession.patient_id == patient_id,
            TrainingSession.exercise_key == exercise_key,
            TrainingSession.completed_at >= since,
            TrainingSession.reps_completed >= target_reps,
        )
        .all()
    )
    collapsed = collapse_training_sessions(rows)
    total = 0
    for s in collapsed:
        bs = int(getattr(s, "bundle_size", None) or 0)
        bp = int(getattr(s, "bundle_part", None) or 0)
        if bs > 1:
            total += max(1, bp) if bp else 1
        else:
            total += 1
    return total


def effective_stats_rows(
    patient_id: int,
    *,
    collapsed: list[TrainingSession] | None = None,
) -> list[dict[str, Any]]:
    """Строки «Детализация по упражнениям» с учётом 1/2 и без дублей."""
    from app.history_sessions import serialize_training_session

    if collapsed is None:
        all_rows = TrainingSession.query.filter_by(patient_id=patient_id).all()
        collapsed = collapse_training_sessions(all_rows)
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in collapsed:
        ser = serialize_training_session(s)
        by_key[ser["exercise_key"]].append(ser)

    out: list[dict[str, Any]] = []
    for key, items in by_key.items():
        items.sort(key=lambda x: x.get("completed_at") or "", reverse=True)
        latest = items[0]
        sessions_n = len(items)
        total_reps = sum(int(x.get("reps_completed") or 0) for x in items)
        scores = [
            int(x.get("score_percent") or 0)
            for x in items
            if not x.get("is_half_of_bundle")
        ]
        if not scores:
            scores = [int(latest.get("score_percent") or 0)]
        avg_score = int(round(sum(scores) / len(scores))) if scores else 0
        summary = latest.get("correctness_summary") or ""
        if "Подход остановлен" in summary:
            status_label = "Подход прерван"
        elif latest.get("is_half_of_bundle"):
            status_label = "Цель не достигнута"
        elif int(latest.get("reps_completed") or 0) >= int(latest.get("target_reps") or 1) and (
            int(latest.get("score_percent") or 0) >= 100 or "Цель достигнута" in summary
        ):
            status_label = "Цель достигнута"
        elif int(latest.get("score_percent") or 0) > 0 or int(latest.get("reps_completed") or 0) > 0:
            status_label = "Частично выполнено"
        else:
            status_label = "Цель не достигнута"
        out.append(
            {
                "exercise_key": key,
                "label": latest.get("exercise_label") or key,
                "sessions": sessions_n,
                "total_reps": total_reps,
                "avg_score": avg_score,
                "last_at": latest.get("completed_at"),
                "bundle_progress_label": latest.get("bundle_progress_label") or "",
                "is_incomplete_bundle": bool(latest.get("is_half_of_bundle")),
                "status_label": status_label,
            }
        )

    out.sort(key=lambda r: str(r.get("last_at") or ""), reverse=True)
    return out
