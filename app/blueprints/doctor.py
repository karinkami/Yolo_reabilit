import uuid

from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from app.exercise_kinds import is_dual_arm_exercise
from app.exercises import EXERCISES
from app.extensions import db
from app.models import Exercise, PatientExerciseAssignment, PatientProfile, User
from app.roles import doctor_required
from app.spa_utils import send_web_spa

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")


@doctor_bp.route("/")
@login_required
@doctor_required
def dashboard():
    return send_web_spa()


@doctor_bp.route("/patient/<int:patient_id>", methods=["GET", "POST"])
@login_required
@doctor_required
def patient_card(patient_id: int):
    if request.method == "GET":
        return send_web_spa()

    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()
    profile = patient.patient_profile
    if profile is None:
        profile = PatientProfile(user_id=patient.id, diagnosis="", notes="")
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        action = request.form.get("action") or ""

        if action == "update_profile":
            profile.diagnosis = (request.form.get("diagnosis") or "").strip()
            profile.notes = (request.form.get("notes") or "").strip()
            db.session.commit()
            flash("Карточка пациента обновлена.", "success")
            return redirect(url_for("doctor.patient_card", patient_id=patient.id))

        if action == "assign_exercise":
            ex_id = request.form.get("exercise_id")
            try:
                ex_id_int = int(ex_id)
            except (TypeError, ValueError):
                ex_id_int = None
            side = request.form.get("side") or "left"
            both_arms = request.form.get("both_arms") == "1"
            try:
                target_reps = int(request.form.get("target_reps") or 10)
            except ValueError:
                target_reps = 10
            target_reps = max(1, min(50, target_reps))
            if side not in ("left", "right"):
                side = "left"

            exercise = db.session.get(Exercise, ex_id_int) if ex_id_int else None
            if exercise is None or exercise.key not in EXERCISES:
                flash("Выберите упражнение из списка.", "danger")
            else:
                both_pair = both_arms
                if both_pair and is_dual_arm_exercise(exercise.key):
                    both_pair = False
                    flash(
                        "Это упражнение уже двустороннее для камеры — создаём одну запись назначения.",
                        "info",
                    )
                if both_pair:
                    gid = str(uuid.uuid4())
                    for s in ("right", "left"):
                        db.session.add(
                            PatientExerciseAssignment(
                                patient_id=patient.id,
                                exercise_id=exercise.id,
                                side=s,
                                target_reps=target_reps,
                                doctor_id=current_user.id,
                                active=True,
                                assignment_group_id=gid,
                            )
                        )
                    db.session.commit()
                    flash(
                        "Назначение для обеих рук добавлено (левая и правая с одинаковым числом повторов).",
                        "success",
                    )
                else:
                    row = PatientExerciseAssignment(
                        patient_id=patient.id,
                        exercise_id=exercise.id,
                        side=side,
                        target_reps=target_reps,
                        doctor_id=current_user.id,
                        active=True,
                    )
                    db.session.add(row)
                    db.session.commit()
                    flash("Назначение добавлено.", "success")
            return redirect(url_for("doctor.patient_card", patient_id=patient.id))

        if action == "deactivate_assignment":
            gid = (request.form.get("assignment_group_id") or "").strip()
            if gid:
                rows = PatientExerciseAssignment.query.filter_by(
                    patient_id=patient.id,
                    assignment_group_id=gid,
                    active=True,
                ).all()
                if rows:
                    for r in rows:
                        r.active = False
                    db.session.commit()
                    flash("Парное назначение снято (обе руки).", "info")
                return redirect(url_for("doctor.patient_card", patient_id=patient.id))

            aid = request.form.get("assignment_id")
            try:
                aid_int = int(aid)
            except (TypeError, ValueError):
                aid_int = None
            row = db.session.get(PatientExerciseAssignment, aid_int) if aid_int else None
            if row and row.patient_id == patient.id:
                row.active = False
                db.session.commit()
                flash("Назначение снято.", "info")
            return redirect(url_for("doctor.patient_card", patient_id=patient.id))

    return redirect(url_for("doctor.patient_card", patient_id=patient.id))
