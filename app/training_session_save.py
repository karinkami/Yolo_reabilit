"""Сохранение результата подхода (завершение цели или остановка пациентом)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.assignment_completion import (
    _successful_sessions_count,
    deactivate_on_success,
    sync_completed_assignments,
)
from app.extensions import db
from app.models import Exercise, PatientExerciseAssignment, TrainingSession


def _score_and_summary(
    *,
    reps: int,
    target: int,
    bundle_part: int | None,
    bundle_size: int | None,
    stopped_early: bool,
    correctness: str,
) -> tuple[int, str]:
    target = max(1, target)
    reps = max(0, min(reps, target))
    score = min(100, max(0, round(100 * reps / target)))

    if bundle_part and bundle_size and int(bundle_size) > 1:
        bp, bs = int(bundle_part), int(bundle_size)
        if bp < bs:
            score = 50
            if stopped_early:
                summary = f"Подход остановлен ({bp}/{bs})"
                if reps > 0:
                    summary = f"Подход остановлен ({bp}/{bs}), {reps}/{target} повт."
            else:
                summary = f"Цель не достигнута ({bp}/{bs})"
        elif reps >= target:
            score = 100
            summary = f"Цель достигнута ({bp}/{bs})"
        elif stopped_early:
            score = min(100, max(0, round(100 * reps / target)))
            summary = f"Подход остановлен ({bp}/{bs}), {reps}/{target} повт."
        else:
            summary = f"Цель не достигнута ({bp}/{bs})"
        return score, summary[:500]

    if stopped_early:
        if reps >= target:
            return 100, (correctness or f"Цель достигнута ({reps}/{target} повт.)")[:500]
        if reps == 0:
            return 0, "Подход остановлен (0 повт.)"
        return score, f"Подход остановлен ({reps}/{target} повт.)"

    summary = correctness or "Завершено"
    if reps >= target:
        if not summary.startswith("Цель"):
            return 100, f"Цель достигнута ({reps}/{target} повт.)"
        return 100, summary[:500]
    if "Цель достигнута" in summary or "Упражнение завершено" in summary:
        return score, f"Частично ({reps}/{target} повт.)"
    return score, summary[:500]


def persist_training_result(
    patient_id: int,
    *,
    assignment_id: int | None,
    exercise_key: str,
    reps: int,
    target_reps: int,
    correctness: str = "",
    stopped_early: bool = False,
) -> dict[str, Any]:
    """
    Записывает подход в training_sessions.
    При stopped_early назначение не снимается, если повторов меньше цели.
    При достижении цели снимается строка или вся связка (правая+левая).
    """
    assignment_completed = False
    side_val = None
    bundle_part = None
    bundle_size = None
    assignment_group_id = None
    assign_row = None

    if assignment_id:
        assign_row = db.session.get(PatientExerciseAssignment, assignment_id)
        if assign_row and assign_row.patient_id == patient_id:
            exercise_key = assign_row.exercise.key
            target_reps = int(assign_row.target_reps)
            reps = max(0, min(int(reps or 0), target_reps))
            if assign_row.side in ("left", "right"):
                side_val = assign_row.side
            gid = assign_row.assignment_group_id
            assignment_group_id = gid
            if gid:
                siblings = (
                    PatientExerciseAssignment.query.filter_by(
                        patient_id=patient_id,
                        assignment_group_id=gid,
                    )
                    .all()
                )
                if len(siblings) >= 2:
                    bundle_size = len(siblings)
                    times = [r.created_at for r in siblings if r.created_at is not None]
                    since = min(times) if times else datetime.utcnow()
                    done_before = _successful_sessions_count(
                        patient_id, exercise_key, since, target_reps
                    )
                    bundle_part = min(done_before + 1, bundle_size)
            if assign_row.active:
                assignment_completed = deactivate_on_success(
                    assign_row,
                    reps,
                    target_reps,
                    bundle_part=bundle_part,
                    bundle_size=bundle_size,
                    stopped_early=stopped_early,
                )

    ex = Exercise.query.filter_by(key=exercise_key).first()
    label = ex.label if ex else exercise_key
    target_reps = max(1, int(target_reps or 10))
    reps = max(0, min(int(reps or 0), target_reps))

    score, summary = _score_and_summary(
        reps=reps,
        target=target_reps,
        bundle_part=bundle_part,
        bundle_size=bundle_size,
        stopped_early=stopped_early,
        correctness=(correctness or "")[:500],
    )

    now = datetime.utcnow()
    session_row = None
    if (
        assignment_group_id
        and bundle_size
        and bundle_part
        and int(bundle_part) >= int(bundle_size)
    ):
        open_row = (
            TrainingSession.query.filter(
                TrainingSession.patient_id == patient_id,
                TrainingSession.assignment_group_id == assignment_group_id,
            )
            .filter(TrainingSession.bundle_part < int(bundle_size))
            .order_by(TrainingSession.id.desc())
            .first()
        )
        if open_row is not None:
            open_row.reps_completed = reps
            open_row.target_reps = target_reps
            open_row.score_percent = score
            open_row.correctness_summary = summary
            open_row.bundle_part = int(bundle_part)
            open_row.bundle_size = int(bundle_size)
            open_row.side = side_val
            open_row.completed_at = now
            session_row = open_row
        else:
            dup = (
                TrainingSession.query.filter(
                    TrainingSession.patient_id == patient_id,
                    TrainingSession.assignment_group_id == assignment_group_id,
                    TrainingSession.bundle_part >= int(bundle_size),
                )
                .order_by(TrainingSession.id.desc())
                .first()
            )
            if dup is not None:
                dup.reps_completed = reps
                dup.target_reps = target_reps
                dup.score_percent = score
                dup.correctness_summary = summary
                dup.completed_at = now
                session_row = dup

    if session_row is None:
        if (
            assignment_group_id
            and bundle_size
            and bundle_part
            and int(bundle_part) < int(bundle_size)
        ):
            TrainingSession.query.filter(
                TrainingSession.patient_id == patient_id,
                TrainingSession.assignment_group_id == assignment_group_id,
                TrainingSession.bundle_part < int(bundle_size),
            ).delete(synchronize_session=False)
        session_row = TrainingSession(
            patient_id=patient_id,
            exercise_key=exercise_key,
            exercise_label=label,
            reps_completed=reps,
            target_reps=target_reps,
            score_percent=score,
            correctness_summary=summary,
            side=side_val,
            bundle_part=bundle_part,
            bundle_size=bundle_size,
            assignment_group_id=assignment_group_id,
        )
        db.session.add(session_row)

    db.session.commit()
    sync_completed_assignments(patient_id)
    db.session.commit()

    bundle_progress_label = ""
    if bundle_size and int(bundle_size) > 1 and bundle_part:
        bundle_progress_label = f"{int(bundle_part)}/{int(bundle_size)}"

    from app.history_sessions import serialize_training_session

    ser = serialize_training_session(session_row)

    return {
        "assignment_completed": assignment_completed,
        "reps_completed": reps,
        "target_reps": target_reps,
        "score_percent": score,
        "correctness_summary": summary,
        "bundle_progress_label": bundle_progress_label or ser.get("bundle_progress_label") or "",
        "is_half_of_bundle": bool(ser.get("is_half_of_bundle")),
        "session": ser,
    }
