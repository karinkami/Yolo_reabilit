"""Снятие назначений после успешных подходов (в т.ч. связка левая+правая)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.models import PatientExerciseAssignment, TrainingSession


def _successful_sessions_count(
    patient_id: int,
    exercise_key: str,
    since: datetime,
    target_reps: int,
) -> int:
    from app.session_aggregate import successful_sides_count

    return successful_sides_count(patient_id, exercise_key, since, target_reps)


def sync_completed_assignments(patient_id: int) -> int:
    """
    Помечает назначения неактивными, если по ним уже есть достаточно успешных сессий.
    Для связки из N сторон (обычно 2) нужно N успешных подходов с момента назначения.
    Возвращает число снятых строк.
    """
    active = (
        PatientExerciseAssignment.query.filter_by(patient_id=patient_id, active=True)
        .all()
    )
    if not active:
        return 0

    groups: dict[str, list[PatientExerciseAssignment]] = defaultdict(list)
    for row in active:
        gid = row.assignment_group_id
        key = str(gid) if gid else f"single-{row.id}"
        groups[key].append(row)

    deactivated = 0
    for rows in groups.values():
        ex = rows[0].exercise
        if ex is None:
            continue
        target = max(1, int(rows[0].target_reps or 10))
        times = [r.created_at for r in rows if r.created_at is not None]
        since = min(times) if times else datetime.utcnow()
        needed = len(rows)
        done = _successful_sessions_count(patient_id, ex.key, since, target)
        if done < needed:
            continue
        for row in rows:
            if row.active:
                row.active = False
                deactivated += 1
    return deactivated


def bundle_progress_for_rows(patient_id: int, rows: list[PatientExerciseAssignment]) -> dict[str, int | str]:
    """Прогресс связки «правая → левая» по числу успешных подходов."""
    total = len(rows)
    if total < 2:
        return {
            "sides_total": max(1, total),
            "sides_done": 0,
            "queue_index": 0,
            "progress_label": "1/1",
            "next_side_label": "",
        }

    ex = rows[0].exercise
    key = ex.key if ex else ""
    target = max(1, int(rows[0].target_reps or 10))
    times = [r.created_at for r in rows if r.created_at is not None]
    since = min(times) if times else datetime.utcnow()
    done = min(_successful_sessions_count(patient_id, key, since, target), total)

    ordered = sorted(rows, key=lambda r: (0 if str(r.side) == "right" else 1, r.id))
    queue_index = min(done, total - 1) if done < total else 0
    next_row = ordered[done] if done < total else None

    from app.side_labels import side_label_full

    next_label = (
        side_label_full(str(next_row.side), key) if next_row is not None and key else ""
    )

    return {
        "sides_total": total,
        "sides_done": done,
        "queue_index": queue_index,
        "progress_label": f"{done}/{total}",
        "next_side_label": next_label,
    }


def deactivate_bundle_group(row: PatientExerciseAssignment) -> bool:
    """Снимает все строки связки (правая+левая / два подхода приседа)."""
    gid = row.assignment_group_id
    if not gid:
        return False
    rows = PatientExerciseAssignment.query.filter_by(
        patient_id=row.patient_id,
        assignment_group_id=gid,
        active=True,
    ).all()
    if not rows:
        return False
    for r in rows:
        r.active = False
    return True


def deactivate_assignment_row(row: PatientExerciseAssignment | None, reps: int, target: int) -> bool:
    """Снимает одно назначение при достижении цели по повторам."""
    if row is None or not row.active:
        return False
    target = max(1, int(target or 10))
    reps = max(0, int(reps or 0))
    if reps < target:
        return False
    if row.assignment_group_id:
        return False
    row.active = False
    return True


def deactivate_on_success(
    row: PatientExerciseAssignment | None,
    reps: int,
    target: int,
    *,
    bundle_part: int | None,
    bundle_size: int | None,
    stopped_early: bool,
) -> bool:
    """
    Снять назначение после достижения цели по повторам.
    Для связки (правая+левая / два подхода приседа) снимаются все строки группы,
    чтобы упражнение исчезало из списка после одного успешного подхода.
    """
    del bundle_part, bundle_size, stopped_early  # сохранены для совместимости вызовов
    if row is None or not row.active:
        return False
    target = max(1, int(target or 10))
    reps = max(0, int(reps or 0))
    if reps < target:
        return False
    if row.assignment_group_id:
        return deactivate_bundle_group(row)
    row.active = False
    return True
