"""JSON API для React-клиента (сессия Flask-Login, cookie)."""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.assignment_completion import sync_completed_assignments
from app.assignment_groups import assignments_for_doctor_display
from app.side_labels import side_label_full
from app.exercise_catalog import (
    CLINICAL_GROUPS,
    COMPLEX_CATALOG_VERSION,
    catalog_for_key,
    complex_by_id,
    exercise_visible_in_doctor_picker,
    serialize_complexes,
)
from app.exercise_kinds import is_dual_arm_exercise
from app.exercises import EXERCISES
from app.extensions import db
from app.models import Exercise, PatientExerciseAssignment, PatientProfile, TrainingSession, User
from app.training_stats import (
    training_chart_last_days,
    training_exercise_distribution,
    training_stats_for_patient,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _json_err(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


def require_login_json(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False):
            return _json_err("Требуется вход", 401)
        return fn(*args, **kwargs)

    return wrapped


def require_role_json(role: str):
    def deco(fn):
        @wraps(fn)
        @require_login_json
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                return _json_err("Недостаточно прав", 403)
            return fn(*args, **kwargs)

        return wrapped

    return deco


def _user_public(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "registration_pending": bool(getattr(u, "registration_pending", False)),
    }


def _patient_list_item(p: User, *, active_assignments_count: int = 0, last_session_at: str | None = None) -> dict:
    u = _user_public(p)
    u["active_assignments_count"] = active_assignments_count
    u["last_session_at"] = last_session_at
    return u


def _serialize_stats_rows(rows: list[dict]) -> list[dict]:
    from app.datetime_util import utc_iso_z

    out = []
    for r in rows:
        d = dict(r)
        la = d.get("last_at")
        if la is not None and hasattr(la, "isoformat"):
            d["last_at"] = utc_iso_z(la)
        elif isinstance(la, str) and la and not la.endswith("Z"):
            d["last_at"] = la.rstrip() + ("Z" if "T" in la else "")
        out.append(d)
    return out


def _last_session_payload(patient_id: int) -> dict | None:
    from app.datetime_util import utc_iso_z
    from app.history_sessions import serialize_training_session
    from app.session_aggregate import collapse_training_sessions

    all_sess = TrainingSession.query.filter_by(patient_id=patient_id).all()
    collapsed = collapse_training_sessions(all_sess)
    if not collapsed:
        return None
    last = max(collapsed, key=lambda s: s.completed_at or datetime.min)
    ser = serialize_training_session(last)
    return {
        "completed_at": ser["completed_at"],
        "exercise_label": ser["exercise_label"],
        "score_percent": ser["score_percent"],
        "reps_completed": ser["reps_completed"],
        "target_reps": ser["target_reps"],
    }


def _patient_stats_bundle(patient_id: int) -> dict:
    stats_rows, stats_summary = training_stats_for_patient(patient_id)
    return {
        "stats_rows": _serialize_stats_rows(stats_rows),
        "stats_summary": stats_summary,
        "stats_chart": training_chart_last_days(patient_id, days=14),
        "stats_exercise_chart": training_exercise_distribution(stats_rows),
        "last_session": _last_session_payload(patient_id),
    }


def _serialize_profile(patient: User, profile: PatientProfile | None) -> dict:
    if profile is None:
        return {
            "full_name_display": patient.full_name,
            "full_name_official": "",
            "birth_date": None,
            "age_years": None,
            "diagnosis": "",
            "comorbidities": "",
            "notes": "",
        }
    official = (profile.full_name_official or "").strip()
    display = official or patient.full_name
    bd = profile.birth_date
    age = None
    if bd is not None:
        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    return {
        "full_name_display": display,
        "full_name_official": official,
        "birth_date": bd.isoformat() if bd else None,
        "age_years": age,
        "diagnosis": profile.diagnosis or "",
        "comorbidities": profile.comorbidities or "",
        "notes": profile.notes or "",
    }


@api_bp.route("/flash", methods=["GET"])
def flash_once():
    from flask import get_flashed_messages

    items = [
        {"category": c, "message": m}
        for c, m in get_flashed_messages(with_categories=True)
    ]
    return jsonify({"items": items})


@api_bp.route("/me", methods=["GET"])
def me():
    if not getattr(current_user, "is_authenticated", False):
        return jsonify({"user": None}), 200
    return jsonify({"user": _user_public(current_user)})


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return _json_err("Неверный email или пароль", 401)
    if getattr(user, "registration_pending", False):
        return _json_err(
            "Аккаунт создан врачом. Завершите регистрацию на странице «Регистрация» с тем же email.",
            403,
        )
    login_user(user, remember=True)
    return jsonify({"ok": True, "user": _user_public(user)})


@api_bp.route("/auth/logout", methods=["POST"])
@require_login_json
def api_logout():
    logout_user()
    return jsonify({"ok": True})


@api_bp.route("/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

    if len(password) < 6:
        return _json_err("Пароль не короче 6 символов")
    if not email or not full_name:
        return _json_err("Заполните все поля")
    existing = User.query.filter_by(email=email).first()
    if existing is not None:
        if existing.role != "patient":
            return _json_err("Этот email уже используется")
        if not getattr(existing, "registration_pending", False):
            return _json_err("Пользователь с таким email уже зарегистрирован")
        existing.set_password(password)
        existing.full_name = full_name
        existing.registration_pending = False
        if existing.patient_profile is None:
            db.session.add(PatientProfile(user_id=existing.id, diagnosis="", notes=""))
        db.session.commit()
        login_user(existing, remember=True)
        return jsonify({"ok": True, "user": _user_public(existing), "completed_invite": True})

    user = User(email=email, full_name=full_name, role="patient", registration_pending=False)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(PatientProfile(user_id=user.id, diagnosis="", notes=""))
    db.session.commit()
    login_user(user, remember=True)
    return jsonify({"ok": True, "user": _user_public(user)})


@api_bp.route("/patient/dashboard", methods=["GET"])
@require_role_json("patient")
def patient_dashboard():
    profile = current_user.patient_profile
    if sync_completed_assignments(current_user.id):
        db.session.commit()
    assignments = (
        PatientExerciseAssignment.query.filter_by(patient_id=current_user.id, active=True)
        .options(joinedload(PatientExerciseAssignment.exercise))
        .order_by(PatientExerciseAssignment.created_at.desc())
        .all()
    )
    todo_plan = assignments_for_doctor_display(assignments, current_user.id)
    stats_bundle = _patient_stats_bundle(current_user.id)

    return jsonify(
        {
            "ok": True,
            "profile": _serialize_profile(current_user, profile),
            "assignments": [
                {
                    "id": a.id,
                    "exercise_key": a.exercise.key,
                    "exercise_label": a.exercise.label,
                    "side": a.side,
                    "side_label": side_label_full(a.side, a.exercise.key),
                    "target_reps": a.target_reps,
                }
                for a in assignments
            ],
            "todo_plan": [
                {
                    "type": row["type"],
                    "ids": row["ids"],
                    "exercise_label": row["exercise_label"],
                    "detail": row["detail"],
                    "primary_id": row["ids"][0],
                }
                for row in todo_plan
            ],
            **stats_bundle,
        }
    )


@api_bp.route("/patient/stats", methods=["GET"])
@require_role_json("patient")
def patient_stats():
    return jsonify({"ok": True, **_patient_stats_bundle(current_user.id)})


@api_bp.route("/doctor/patients", methods=["GET"])
@require_role_json("doctor")
def doctor_patients():
    from app.datetime_util import utc_iso_z

    patients = User.query.filter_by(role="patient").order_by(User.full_name.asc()).all()
    pids = [p.id for p in patients]
    cnt: dict[int, int] = {pid: 0 for pid in pids}
    last_at: dict[int, object] = {}
    if pids:
        for pid, n in (
            db.session.query(
                PatientExerciseAssignment.patient_id,
                func.count(PatientExerciseAssignment.id),
            )
            .filter(
                PatientExerciseAssignment.patient_id.in_(pids),
                PatientExerciseAssignment.active.is_(True),
            )
            .group_by(PatientExerciseAssignment.patient_id)
            .all()
        ):
            cnt[int(pid)] = int(n)
        for pid, ts in (
            db.session.query(
                TrainingSession.patient_id,
                func.max(TrainingSession.completed_at),
            )
            .filter(TrainingSession.patient_id.in_(pids))
            .group_by(TrainingSession.patient_id)
            .all()
        ):
            last_at[int(pid)] = ts

    out = []
    for p in patients:
        ts = last_at.get(p.id)
        out.append(
            _patient_list_item(
                p,
                active_assignments_count=cnt.get(p.id, 0),
                last_session_at=utc_iso_z(ts) if ts else None,
            )
        )

    return jsonify({"ok": True, "patients": out})


@api_bp.route("/doctor/patients", methods=["POST"])
@require_role_json("doctor")
def doctor_create_patient():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    full_name = (data.get("full_name") or "").strip()

    if not email or "@" not in email:
        return _json_err("Укажите корректный email")
    if not full_name:
        return _json_err("Укажите ФИО пациента")

    existing = User.query.filter_by(email=email).first()
    if existing is not None:
        if existing.role != "patient":
            return _json_err("Этот email уже занят другой учётной записью")
        if not getattr(existing, "registration_pending", False):
            return _json_err("Пациент с таким email уже зарегистрирован")
        existing.full_name = full_name
        db.session.commit()
        return jsonify(
            {
                "ok": True,
                "patient": _patient_list_item(existing),
                "message": "Карточка обновлена. Пациент по-прежнему должен завершить регистрацию.",
            }
        )

    user = User(
        email=email,
        full_name=full_name,
        role="patient",
        registration_pending=True,
    )
    user.set_password(secrets.token_urlsafe(32))
    db.session.add(user)
    db.session.flush()
    db.session.add(PatientProfile(user_id=user.id, diagnosis="", notes=""))
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "patient": _patient_list_item(user),
            "message": "Пациент создан. Он должен зарегистрироваться с этим email и задать пароль.",
        }
    )


@api_bp.route("/doctor/patient/<int:patient_id>", methods=["DELETE"])
@require_role_json("doctor")
def doctor_delete_patient(patient_id: int):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    db.session.delete(patient)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/doctor/patient/<int:patient_id>", methods=["GET"])
@require_role_json("doctor")
def doctor_patient_detail(patient_id: int):
    try:
        return _doctor_patient_detail_payload(patient_id)
    except Exception:
        current_app.logger.exception("doctor_patient_detail patient_id=%s", patient_id)
        return _json_err("Не удалось загрузить карточку пациента", 500)


def _doctor_patient_detail_payload(patient_id: int):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    profile = patient.patient_profile
    if profile is None:
        profile = PatientProfile(user_id=patient.id, diagnosis="", notes="")
        db.session.add(profile)
        db.session.commit()

    exercises = (
        Exercise.query.filter(Exercise.key.in_(tuple(EXERCISES.keys())))
        .order_by(Exercise.label.asc())
        .all()
    )
    assignments = (
        PatientExerciseAssignment.query.filter_by(patient_id=patient.id, active=True)
        .order_by(PatientExerciseAssignment.created_at.desc())
        .all()
    )
    stats_rows, stats_summary = training_stats_for_patient(patient.id)
    stats_chart = training_chart_last_days(patient.id, days=14)
    stats_exercise_chart = training_exercise_distribution(stats_rows)
    assignment_display = assignments_for_doctor_display(assignments, patient.id)

    last_session = _last_session_payload(patient.id)

    def _row(r):
        d = {k: v for k, v in r.items() if k != "created_at"}
        ca = r.get("created_at")
        if ca is not None and hasattr(ca, "isoformat"):
            from app.datetime_util import utc_iso_z

            d["created_at"] = utc_iso_z(ca)
        return d

    labels = {e.key: e.label for e in exercises}
    picker_exercises = [e for e in exercises if exercise_visible_in_doctor_picker(e.key)]

    resp = jsonify(
        {
            "ok": True,
            "patient": _user_public(patient),
            "profile": _serialize_profile(patient, profile),
            "exercises": [
                {"id": e.id, "key": e.key, "label": e.label, **catalog_for_key(e.key)}
                for e in picker_exercises
            ],
            "clinical_groups": [{"id": gid, "label": lab} for gid, lab in CLINICAL_GROUPS],
            "assignment_complexes": serialize_complexes(labels),
            "complex_catalog_version": COMPLEX_CATALOG_VERSION,
            "assignment_display": [_row(r) for r in assignment_display],
            "stats_rows": _serialize_stats_rows(stats_rows),
            "stats_summary": stats_summary,
            "stats_chart": stats_chart,
            "stats_exercise_chart": stats_exercise_chart,
            "last_session": last_session,
        }
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@api_bp.route("/doctor/patient/<int:patient_id>/profile", methods=["POST"])
@require_role_json("doctor")
def doctor_patient_profile(patient_id: int):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    profile = patient.patient_profile
    if profile is None:
        profile = PatientProfile(user_id=patient.id, diagnosis="", notes="")
        db.session.add(profile)
    data = request.get_json(silent=True) or {}
    profile.full_name_official = (data.get("full_name_official") or "").strip()[:200]
    raw_bd = (data.get("birth_date") or "").strip()
    if raw_bd:
        try:
            profile.birth_date = date.fromisoformat(raw_bd[:10])
        except ValueError:
            pass
    else:
        profile.birth_date = None
    profile.diagnosis = (data.get("diagnosis") or "").strip()
    profile.comorbidities = (data.get("comorbidities") or "").strip()
    profile.notes = (data.get("notes") or "").strip()
    db.session.commit()
    return jsonify({"ok": True})


def _add_exercise_assignment(
    patient: User,
    exercise: Exercise,
    *,
    side: str,
    target_reps: int,
    both_arms: bool,
    doctor_id: int,
) -> int:
    """Создаёт одно или два (левая+правая) назначения. Возвращает число созданных строк."""
    both_pair = both_arms and not is_dual_arm_exercise(exercise.key)
    if both_pair:
        gid = str(uuid.uuid4())
        for s in ("left", "right"):
            db.session.add(
                PatientExerciseAssignment(
                    patient_id=patient.id,
                    exercise_id=exercise.id,
                    side=s,
                    target_reps=target_reps,
                    doctor_id=doctor_id,
                    active=True,
                    assignment_group_id=gid,
                )
            )
        return 2
    db.session.add(
        PatientExerciseAssignment(
            patient_id=patient.id,
            exercise_id=exercise.id,
            side=side,
            target_reps=target_reps,
            doctor_id=doctor_id,
            active=True,
        )
    )
    return 1


def _apply_assignment_complex(
    patient: User,
    complex_def: dict,
    *,
    doctor_id: int,
    exercises_by_key: dict[str, Exercise],
) -> tuple[int, list[str]]:
    """Назначает все упражнения комплекса. Возвращает (число строк, список ошибок)."""
    created = 0
    errors: list[str] = []
    seen_keys: set[str] = set()
    for item in complex_def.get("items") or []:
        key = item.get("exercise_key")
        if not key:
            errors.append("Пустой ключ упражнения в комплексе")
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if key not in EXERCISES:
            errors.append(f"Неизвестное упражнение: {key}")
            continue
        exercise = exercises_by_key.get(key)
        if exercise is None:
            errors.append(f"Упражнение «{key}» не найдено в базе")
            continue
        try:
            reps = int(item.get("target_reps") or 10)
        except (TypeError, ValueError):
            reps = 10
        reps = max(1, min(50, reps))
        # В комплексе всегда левая + правая (кроме дыхания — обе руки синхронно, одна запись).
        both_pair = not is_dual_arm_exercise(exercise.key)
        created += _add_exercise_assignment(
            patient,
            exercise,
            side="left",
            target_reps=reps,
            both_arms=both_pair,
            doctor_id=doctor_id,
        )
    return created, errors


@api_bp.route("/doctor/patient/<int:patient_id>/assign", methods=["POST"])
@require_role_json("doctor")
def doctor_patient_assign(patient_id: int):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    data = request.get_json(silent=True) or {}
    try:
        ex_id_int = int(data.get("exercise_id"))
    except (TypeError, ValueError):
        return _json_err("Выберите упражнение")
    side = data.get("side") or "left"
    both_arms = bool(data.get("both_arms"))
    try:
        target_reps = int(data.get("target_reps") or 10)
    except ValueError:
        target_reps = 10
    target_reps = max(1, min(50, target_reps))
    if side not in ("left", "right"):
        side = "left"

    exercise = db.session.get(Exercise, ex_id_int)
    if exercise is None or exercise.key not in EXERCISES:
        return _json_err("Выберите упражнение из списка")

    _add_exercise_assignment(
        patient,
        exercise,
        side=side,
        target_reps=target_reps,
        both_arms=both_arms,
        doctor_id=current_user.id,
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/doctor/patient/<int:patient_id>/assign-complex", methods=["POST"])
@require_role_json("doctor")
def doctor_patient_assign_complex(patient_id: int):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    data = request.get_json(silent=True) or {}
    complex_id = (data.get("complex_id") or "").strip()
    if not complex_id:
        return _json_err("Выберите комплекс упражнений")

    complex_def = complex_by_id(complex_id)
    if complex_def is None:
        return _json_err("Комплекс не найден")

    exercises = (
        Exercise.query.filter(Exercise.key.in_(tuple(EXERCISES.keys()))).all()
    )
    by_key = {e.key: e for e in exercises}

    created, errors = _apply_assignment_complex(
        patient,
        complex_def,
        doctor_id=current_user.id,
        exercises_by_key=by_key,
    )
    if created == 0:
        return _json_err(errors[0] if errors else "Не удалось назначить комплекс")

    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "assigned_count": created,
            "complex_label": complex_def["label"],
            "warnings": errors,
        }
    )


@api_bp.route("/doctor/patient/<int:patient_id>/deactivate", methods=["POST"])
@require_role_json("doctor")
def doctor_patient_deactivate(patient_id: int):
    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    data = request.get_json(silent=True) or {}
    gid = (data.get("assignment_group_id") or "").strip()
    if gid:
        rows = PatientExerciseAssignment.query.filter_by(
            patient_id=patient.id,
            assignment_group_id=gid,
            active=True,
        ).all()
        for r in rows:
            r.active = False
        db.session.commit()
        return jsonify({"ok": True})

    try:
        aid_int = int(data.get("assignment_id"))
    except (TypeError, ValueError):
        return _json_err("Некорректное назначение")
    row = db.session.get(PatientExerciseAssignment, aid_int)
    if row and row.patient_id == patient.id:
        row.active = False
        db.session.commit()
    return jsonify({"ok": True})
