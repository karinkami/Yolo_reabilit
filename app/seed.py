import os

from app.extensions import db
from app.models import Exercise, PatientExerciseAssignment, User


def seed_exercises():
    catalog = [
        ("shoulder_abduction", "Отведение руки в сторону"),
        ("recovery_abduction", "Отведение в сторону (лёгкая амплитуда)"),
        ("forward_raise", "Подъём руки вперёд"),
        ("scaption_raise", "Подъём по плоскости лопатки (скапция)"),
        ("arm_raise", "Подъём руки вверх"),
        ("breathing_arms", "Дыхание: подъём обеих рук"),
        ("breathing_arms_slow", "Дыхание: медленные циклы с руками"),
        ("partial_squat", "Частичное приседание (контроль колена)"),
        ("elbow_flexion", "Сгибание в локте у корпуса"),
        ("knee_extension", "Разгибание колена (сидя)"),
    ]
    valid_keys = {k for k, _ in catalog}

    for ex in Exercise.query.all():
        if ex.key not in valid_keys:
            for a in PatientExerciseAssignment.query.filter_by(exercise_id=ex.id).all():
                db.session.delete(a)
            db.session.delete(ex)

    for key, label in catalog:
        row = Exercise.query.filter_by(key=key).first()
        if row is None:
            db.session.add(Exercise(key=key, label=label))
        elif row.label != label:
            row.label = label

    db.session.commit()


def seed_demo_doctor():
    if User.query.filter_by(role="doctor").first():
        return
    email = os.environ.get("SEED_DOCTOR_EMAIL", "doctor@clinic.local")
    password = os.environ.get("SEED_DOCTOR_PASSWORD", "doctor123")
    if User.query.filter_by(email=email).first():
        return
    u = User(email=email, full_name="Врач (демо)", role="doctor")
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
