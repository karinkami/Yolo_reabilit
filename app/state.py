"""Состояние тренировки с камерой — отдельно для каждого пациента (user id)."""

from __future__ import annotations

import copy
import threading
from typing import Any

_state_lock = threading.Lock()
_user_states: dict[int, dict[str, Any]] = {}

_INITIAL: dict[str, Any] = {
    "selected_exercise": "shoulder_abduction",
    "session_active": False,
    "target_reps": 10,
    "active_side": "left",
    "assignment_id": None,
    "feedback": "Ожидание...",
    "angle": 0,
    "phase": "start",
    "reps": 0,
    "correctness": "Коррекция",
    "completed": False,
    "tips": [
        "Встаньте боком к камере: рабочая сторона ближе к объективу.",
        "В кадре — силуэт корпуса сбоку, плечо, локоть и кисть рабочей руки.",
        "Движения плавные, корпус без наклона и рывков.",
    ],
}


def get_state(user_id: int) -> dict[str, Any]:
    with _state_lock:
        if user_id not in _user_states:
            _user_states[user_id] = copy.deepcopy(_INITIAL)
        return dict(_user_states[user_id])


def update_state(user_id: int, **kwargs: Any) -> None:
    with _state_lock:
        if user_id not in _user_states:
            _user_states[user_id] = copy.deepcopy(_INITIAL)
        _user_states[user_id].update(kwargs)


def reset_state(user_id: int) -> None:
    """Сброс активной сессии камеры; назначение врача (assignment_id, упражнение, сторона, цель) сохраняем."""
    with _state_lock:
        if user_id not in _user_states:
            return
        st = _user_states[user_id]
        preserved = {
            "assignment_id": st.get("assignment_id"),
            "selected_exercise": st.get("selected_exercise"),
            "active_side": st.get("active_side"),
            "target_reps": st.get("target_reps"),
        }
        _user_states[user_id] = copy.deepcopy(_INITIAL)
        _user_states[user_id].update(preserved)


def active_session_user_id(exclude_user_id: int | None = None) -> int | None:
    """Если у кого-то уже session_active — вернуть его id (для защиты одной камеры на процесс)."""
    with _state_lock:
        for uid, st in _user_states.items():
            if exclude_user_id is not None and uid == exclude_user_id:
                continue
            if st.get("session_active"):
                return int(uid)
        return None
