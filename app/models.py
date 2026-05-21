from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    registration_pending = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient_profile = db.relationship(
        "PatientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    assignments = db.relationship(
        "PatientExerciseAssignment",
        foreign_keys="PatientExerciseAssignment.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    training_sessions = db.relationship(
        "TrainingSession",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class PatientProfile(db.Model):
    """Карточка пациента. Поле notes — персональные рекомендации врача, показываются на странице тренировки."""

    __tablename__ = "patient_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    full_name_official = db.Column(db.String(200), default="", nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    diagnosis = db.Column(db.Text, default="", nullable=False)
    comorbidities = db.Column(db.Text, default="", nullable=False)
    notes = db.Column(db.Text, default="", nullable=False)  # персональные рекомендации для тренировки
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="patient_profile")


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    label = db.Column(db.String(200), nullable=False)

    assignments = db.relationship("PatientExerciseAssignment", back_populates="exercise")
    guide = db.relationship(
        "ExerciseGuide",
        back_populates="exercise",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ExerciseGuide(db.Model):
    __tablename__ = "exercise_guides"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(
        db.Integer, db.ForeignKey("exercises.id"), unique=True, nullable=False
    )
    title = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    what_counts = db.Column(db.Text, nullable=False, default="")
    how_to = db.Column(db.JSON, nullable=False, default=list)
    mistakes = db.Column(db.JSON, nullable=False, default=list)

    exercise = db.relationship("Exercise", back_populates="guide")


class PatientExerciseAssignment(db.Model):
    __tablename__ = "patient_exercise_assignments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    side = db.Column(db.String(10), nullable=False, default="left")
    target_reps = db.Column(db.Integer, nullable=False, default=10)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    assignment_group_id = db.Column(db.String(36), nullable=True, index=True)

    patient = db.relationship("User", foreign_keys=[patient_id], back_populates="assignments")
    exercise = db.relationship("Exercise", back_populates="assignments")
    doctor = db.relationship("User", foreign_keys=[doctor_id])


class TrainingSession(db.Model):
    __tablename__ = "training_sessions"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    exercise_key = db.Column(db.String(64), nullable=False)
    exercise_label = db.Column(db.String(200), default="", nullable=False)
    reps_completed = db.Column(db.Integer, nullable=False)
    target_reps = db.Column(db.Integer, nullable=False)
    score_percent = db.Column(db.Integer, nullable=False)
    correctness_summary = db.Column(db.String(500), default="", nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    side = db.Column(db.String(10), nullable=True)
    bundle_part = db.Column(db.Integer, nullable=True)
    bundle_size = db.Column(db.Integer, nullable=True)
    assignment_group_id = db.Column(db.String(36), nullable=True, index=True)

    patient = db.relationship("User", back_populates="training_sessions")
