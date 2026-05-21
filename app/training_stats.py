"""Агрегированная статистика завершённых тренировок по пациенту."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from app.datetime_util import local_date_start_utc_naive, utc_iso_z, utc_naive_to_local_date
from app.models import TrainingSession
from app.session_aggregate import collapse_training_sessions, effective_stats_rows


def training_stats_for_patient(patient_id: int) -> tuple[list[dict], dict]:
    """
    Возвращает (строки по упражнениям, сводка).
    Без дублей связок; 1/2 показывается как 50%, в среднюю оценку не входит.
    """
    all_sess = TrainingSession.query.filter_by(patient_id=patient_id).all()
    collapsed = collapse_training_sessions(all_sess)
    stats_rows = effective_stats_rows(patient_id, collapsed=collapsed)

    total_sessions = len(collapsed)
    total_reps = sum(r["total_reps"] for r in stats_rows)
    if collapsed:
        from app.history_sessions import serialize_training_session, stats_score_eligible

        serialized = [serialize_training_session(s) for s in collapsed]
        scores = [
            int(ser["score_percent"])
            for ser in serialized
            if stats_score_eligible(ser)
        ]
        if not scores:
            scores = [int(ser["score_percent"]) for ser in serialized]
        avg_score = int(round(sum(scores) / len(scores)))
        best_score = max(scores)
    else:
        avg_score = 0
        best_score = None

    week_ago = datetime.utcnow() - timedelta(days=7)
    collapsed_7d = collapse_training_sessions(
        [s for s in all_sess if s.completed_at and s.completed_at >= week_ago]
    )
    sessions_7d = len(collapsed_7d)

    last = max(collapsed, key=lambda s: s.completed_at or datetime.min, default=None)
    last_at = last.completed_at if last is not None else None

    chart_14 = training_chart_last_days(patient_id, days=14)
    active_days_14 = sum(1 for n in chart_14.get("session_counts", []) if n > 0)

    summary = {
        "total_sessions": int(total_sessions),
        "exercise_kinds": len(stats_rows),
        "total_reps": int(total_reps),
        "avg_score": avg_score,
        "sessions_last_7_days": int(sessions_7d),
        "active_days_last_14": int(active_days_14),
        "best_score": int(best_score) if best_score is not None else None,
        "last_session_at": utc_iso_z(last_at),
    }
    return stats_rows, summary


def training_exercise_distribution(stats_rows: list[dict], limit: int = 8) -> dict | None:
    """Доля подходов по упражнениям (для круговой диаграммы)."""
    top = sorted(stats_rows, key=lambda r: int(r.get("sessions") or 0), reverse=True)[:limit]
    if not top:
        return None
    return {
        "labels": [str(r["label"]) for r in top],
        "session_counts": [int(r["sessions"]) for r in top],
    }


def training_chart_last_days(patient_id: int, days: int = 14) -> dict:
    """Данные для графика: по дням число завершённых сессий и средняя оценка (%, по дню)."""
    from app.history_sessions import serialize_training_session, stats_score_eligible

    days = max(7, min(int(days), 60))
    end_d = datetime.now().astimezone().date()
    start_d = end_d - timedelta(days=days - 1)
    since = local_date_start_utc_naive(start_d)

    rows = (
        TrainingSession.query.filter(
            TrainingSession.patient_id == patient_id,
            TrainingSession.completed_at >= since,
        )
        .order_by(TrainingSession.completed_at.asc())
        .all()
    )
    collapsed = collapse_training_sessions(rows)

    bucket: dict[str, dict] = defaultdict(lambda: {"n": 0, "scores": []})
    for s in collapsed:
        if s.completed_at is None:
            continue
        local_d = utc_naive_to_local_date(s.completed_at)
        if local_d is None:
            continue
        dkey = local_d.isoformat()
        bucket[dkey]["n"] += 1
        ser = serialize_training_session(s)
        if stats_score_eligible(ser):
            bucket[dkey]["scores"].append(int(ser.get("score_percent") or 0))

    labels: list[str] = []
    counts: list[int] = []
    avg_scores: list[float] = []
    cur: date = start_d
    end: date = end_d
    while cur <= end:
        key = cur.isoformat()
        labels.append(cur.strftime("%d.%m"))
        info = bucket.get(key, {"n": 0, "scores": []})
        counts.append(int(info["n"]))
        sc = info["scores"]
        avg_scores.append(round(sum(sc) / len(sc), 1) if sc else 0.0)
        cur += timedelta(days=1)

    return {
        "labels": labels,
        "session_counts": counts,
        "avg_scores": avg_scores,
        "days": days,
    }
