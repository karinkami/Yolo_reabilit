"""ISO-строки UTC для JSON (без «+00:00Z», из-за которого в браузере NaN)."""

from __future__ import annotations

from datetime import date, datetime, timezone


def utc_iso_z(dt: datetime | None) -> str | None:
    """Naive datetime из БД трактуем как UTC; в JSON — ``...T12:00:00Z``."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def utc_naive_to_local_date(dt: datetime | None) -> date | None:
    """Календарный день в часовом поясе сервера (для графиков и группировки)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date()


def local_date_start_utc_naive(d: date) -> datetime:
    """Полночь локального дня → naive UTC для сравнения с ``completed_at`` в БД."""
    tz = datetime.now().astimezone().tzinfo
    local_mid = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    return local_mid.astimezone(timezone.utc).replace(tzinfo=None)
