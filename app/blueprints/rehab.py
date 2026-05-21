from flask import Blueprint, Response, jsonify, request, url_for

from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app.camera import generate_frames, prepare_training_camera, stop_training_camera
from app.assignment_completion import sync_completed_assignments
from app.training_session_save import persist_training_result
from app.assignment_groups import enrich_option_for_template, rehab_select_options
from app.exercise_guides import get_guides
from app.extensions import db
from app.models import PatientExerciseAssignment, PatientProfile
from app.roles import patient_required
from app.spa_utils import send_web_spa
from app.side_labels import side_prepare_feedback
from app.state import active_session_user_id, get_state, reset_state, update_state

rehab_bp = Blueprint("rehab", __name__, url_prefix="/patient/rehab")


def _uid() -> int:
    return int(current_user.id)


@rehab_bp.route("/")
@login_required
@patient_required
def training():
    return send_web_spa()


@rehab_bp.route("/api/bootstrap")
@login_required
@patient_required
def api_bootstrap():
    if sync_completed_assignments(current_user.id):
        db.session.commit()
    assignments = (
        PatientExerciseAssignment.query.filter_by(patient_id=current_user.id, active=True)
        .options(joinedload(PatientExerciseAssignment.exercise))
        .order_by(PatientExerciseAssignment.created_at.desc())
        .all()
    )
    raw_opts = rehab_select_options(assignments)
    rehab_options = [enrich_option_for_template(o, current_user.id) for o in raw_opts]
    profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
    personal_recommendations = (profile.notes or "").strip() if profile else ""
    return jsonify(
        {
            "ok": True,
            "hasAssignments": bool(rehab_options),
            "options": rehab_options,
            "personalRecommendations": personal_recommendations,
            "urls": {
                "selectExercise": url_for("rehab.select_exercise"),
                "settings": url_for("rehab.update_settings"),
                "feedback": url_for("rehab.feedback"),
                "videoFeed": url_for("rehab.video_feed"),
                "start": url_for("rehab.start"),
                "stop": url_for("rehab.stop"),
                "complete": url_for("rehab.training_complete"),
                "guides": url_for("rehab.api_guides"),
            },
        }
    )


@rehab_bp.route("/select_exercise", methods=["POST"])
@login_required
@patient_required
def select_exercise():
    data = request.get_json(silent=True) or {}
    aid = data.get("assignment_id")
    try:
        aid = int(aid) if aid is not None else None
    except (TypeError, ValueError):
        aid = None

    if not aid:
        return jsonify(
            {"status": "error", "message": "Выберите назначение врача из списка."}
        ), 400

    row = db.session.get(PatientExerciseAssignment, aid)
    if not row or row.patient_id != current_user.id or not row.active:
        return jsonify({"status": "error", "message": "Недопустимое назначение"}), 403

    update_state(
        _uid(),
        selected_exercise=row.exercise.key,
        active_side=row.side,
        target_reps=row.target_reps,
        assignment_id=row.id,
    )
    return jsonify(
        {
            "status": "ok",
            "exercise": row.exercise.key,
            "side": row.side,
            "target_reps": row.target_reps,
            "assignment_id": row.id,
        }
    )


@rehab_bp.route("/api/settings", methods=["POST"])
@login_required
@patient_required
def update_settings():
    """При активном назначении сторона и число повторов только из записи врача — с клиента не меняются."""
    data = request.get_json(silent=True) or {}
    uid = _uid()
    st = get_state(uid)
    aid = st.get("assignment_id")
    locked = False

    if aid:
        row = db.session.get(PatientExerciseAssignment, aid)
        if row and row.patient_id == current_user.id and row.active:
            side = row.side if row.side in ("left", "right") else "left"
            target = int(row.target_reps)
            locked = True
        else:
            side = data.get("side", "left")
            if side not in ("left", "right"):
                side = "left"
            try:
                target = int(data.get("target_reps", st.get("target_reps") or 10))
            except (TypeError, ValueError):
                target = int(st.get("target_reps") or 10)
            target = max(1, min(50, target))
    else:
        side = data.get("side", "left")
        if side not in ("left", "right"):
            side = "left"
        try:
            target = int(data.get("target_reps", st.get("target_reps") or 10))
        except (TypeError, ValueError):
            target = int(st.get("target_reps") or 10)
        target = max(1, min(50, target))

    update_state(uid, active_side=side, target_reps=target)
    return jsonify(
        {
            "status": "ok",
            "side": side,
            "target_reps": target,
            "assignment_locked": locked,
        }
    )


@rehab_bp.route("/api/feedback")
@login_required
@patient_required
def feedback():
    st = get_state(_uid())
    out = dict(st)
    out["assignment_locked"] = bool(st.get("assignment_id"))
    return jsonify(out)


@rehab_bp.route("/api/guides")
@login_required
@patient_required
def api_guides():
    """Подробные инструкции по ключу упражнения (из таблицы exercise_guides)."""
    return jsonify(get_guides())


@rehab_bp.route("/video_feed")
@login_required
@patient_required
def video_feed():
    uid = _uid()
    return Response(
        generate_frames(uid),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@rehab_bp.route("/api/start", methods=["POST"])
@login_required
@patient_required
def start():
    data = request.get_json(silent=True) or {}
    uid = _uid()
    other = active_session_user_id(exclude_user_id=uid)
    if other is not None:
        return jsonify(
            {
                "status": "error",
                "code": "session_busy",
                "message": "На сервере уже идёт другая активная тренировка. Дождитесь её завершения или остановите её.",
            }
        ), 409

    st = get_state(uid)
    aid = st.get("assignment_id")
    try:
        body_aid = data.get("assignment_id")
        if body_aid is not None:
            aid = int(body_aid)
    except (TypeError, ValueError):
        pass
    if not aid:
        return jsonify(
            {
                "status": "error",
                "message": "Сначала выберите назначение врача в списке на странице.",
            }
        ), 400

    row = db.session.get(PatientExerciseAssignment, aid)
    if not row or row.patient_id != current_user.id or not row.active:
        return jsonify(
            {"status": "error", "message": "Назначение недействительно. Обновите страницу."}
        ), 400

    ex_key = row.exercise.key
    stream_gen = prepare_training_camera(uid)
    update_state(
        uid,
        assignment_id=row.id,
        target_reps=row.target_reps,
        active_side=row.side,
        selected_exercise=ex_key,
        session_active=True,
        completed=False,
        reps=0,
        phase="start",
        feedback=side_prepare_feedback(row.side, ex_key),
    )
    return jsonify({"status": "started", "stream_gen": stream_gen})


@rehab_bp.route("/api/stop", methods=["POST"])
@login_required
@patient_required
def stop():
    data = request.get_json(silent=True) or {}
    uid = _uid()
    st = get_state(uid)
    was_active = bool(st.get("session_active"))
    try:
        reps = int(data.get("reps") if data.get("reps") is not None else st.get("reps") or 0)
    except (TypeError, ValueError):
        reps = int(st.get("reps") or 0)
    try:
        target = int(
            data.get("target_reps") if data.get("target_reps") is not None else st.get("target_reps") or 10
        )
    except (TypeError, ValueError):
        target = int(st.get("target_reps") or 10)
    correctness = (data.get("correctness") or st.get("correctness") or "")[:500]
    aid = st.get("assignment_id")

    stop_training_camera(uid)
    reset_state(uid)

    saved_payload = None
    if was_active and aid:
        try:
            saved_payload = persist_training_result(
                current_user.id,
                assignment_id=int(aid),
                exercise_key=(st.get("selected_exercise") or "shoulder_abduction"),
                reps=reps,
                target_reps=target,
                correctness=correctness,
                stopped_early=True,
            )
        except Exception:
            db.session.rollback()
            return jsonify(
                {
                    "status": "stopped",
                    "saved": False,
                    "message": "Подход остановлен, но результат не сохранился. Повторите позже.",
                }
            ), 500

    out = {"status": "stopped", "saved": saved_payload is not None}
    if saved_payload:
        out.update(
            {
                "reps_completed": saved_payload["reps_completed"],
                "target_reps": saved_payload["target_reps"],
                "score_percent": saved_payload["score_percent"],
                "correctness_summary": saved_payload["correctness_summary"],
                "bundle_progress_label": saved_payload["bundle_progress_label"],
                "is_half_of_bundle": saved_payload["is_half_of_bundle"],
            }
        )
    return jsonify(out)


@rehab_bp.route("/api/complete", methods=["POST"])
@login_required
@patient_required
def training_complete():
    data = request.get_json(silent=True) or {}
    uid = _uid()
    st = get_state(uid)
    aid = st.get("assignment_id")
    try:
        body_aid = data.get("assignment_id")
        if body_aid is not None:
            aid = int(body_aid)
    except (TypeError, ValueError):
        pass
    exercise_key = (data.get("exercise_key") or "").strip() or st.get("selected_exercise") or "shoulder_abduction"
    try:
        reps = int(data.get("reps") or 0)
    except (TypeError, ValueError):
        reps = 0
    try:
        target = int(data.get("target_reps") or st.get("target_reps") or 10)
    except (TypeError, ValueError):
        target = 10
    correctness = (data.get("correctness") or "")[:500]

    if not aid:
        return jsonify({"status": "error", "message": "Нет активного назначения."}), 400

    try:
        result = persist_training_result(
            current_user.id,
            assignment_id=int(aid),
            exercise_key=exercise_key,
            reps=reps,
            target_reps=target,
            correctness=correctness,
            stopped_early=False,
        )
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Не удалось сохранить результат."}), 500
    return jsonify(
        {
            "status": "ok",
            "assignment_completed": result["assignment_completed"],
            "session": result.get("session"),
            "score_percent": result.get("score_percent"),
            "correctness_summary": result.get("correctness_summary"),
            "bundle_progress_label": result.get("bundle_progress_label"),
        }
    )
