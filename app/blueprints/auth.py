from flask import Blueprint, flash, redirect, request, url_for
from flask_login import login_user, logout_user

from app.extensions import db
from app.models import PatientProfile, User
from app.spa_utils import send_web_spa

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("Неверный email или пароль.", "danger")
            return send_web_spa()

        if getattr(user, "registration_pending", False):
            flash(
                "Аккаунт создан врачом. Завершите регистрацию на странице «Регистрация» с тем же email.",
                "warning",
            )
            return send_web_spa()

        login_user(user, remember=True)
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)
        if user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("patient.dashboard"))

    return send_web_spa()


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        full_name = (request.form.get("full_name") or "").strip()

        if len(password) < 6:
            flash("Пароль должен быть не короче 6 символов.", "danger")
            return send_web_spa()

        if not email or not full_name:
            flash("Заполните все поля.", "danger")
            return send_web_spa()

        existing = User.query.filter_by(email=email).first()
        if existing is not None:
            if existing.role != "patient":
                flash("Этот email уже используется.", "danger")
                return send_web_spa()
            if not getattr(existing, "registration_pending", False):
                flash("Пользователь с таким email уже зарегистрирован.", "danger")
                return send_web_spa()
            existing.set_password(password)
            existing.full_name = full_name
            existing.registration_pending = False
            if existing.patient_profile is None:
                db.session.add(PatientProfile(user_id=existing.id, diagnosis="", notes=""))
            db.session.commit()
            login_user(existing, remember=True)
            flash("Регистрация завершена. Добро пожаловать!", "success")
            return redirect(url_for("patient.dashboard"))

        user = User(email=email, full_name=full_name, role="patient", registration_pending=False)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(PatientProfile(user_id=user.id, diagnosis="", notes=""))
        db.session.commit()
        login_user(user, remember=True)
        flash("Регистрация прошла успешно.", "success")
        return redirect(url_for("patient.dashboard"))

    return send_web_spa()
