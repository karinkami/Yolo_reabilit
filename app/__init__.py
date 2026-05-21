import os
from pathlib import Path

from flask import Flask, redirect, send_from_directory, url_for
from flask_login import current_user

from app.blueprints.api import api_bp
from app.blueprints.auth import auth_bp
from app.blueprints.doctor import doctor_bp
from app.blueprints.patient import patient_bp
from app.blueprints.rehab import rehab_bp
from app.extensions import db, login_manager
from app.models import User
from app.seed import seed_demo_doctor, seed_exercises
from app.schema_patch import (
    ensure_assignment_columns,
    ensure_patient_profile_columns,
    ensure_training_session_columns,
    ensure_user_columns,
)
from app.settings_loader import (
    flask_safe_secret_key,
    load_app_settings,
    resolve_database_uri,
    secret_key_from_settings,
)


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    json_settings = load_app_settings()
    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    raw_secret = (
        os.environ.get("SECRET_KEY")
        or secret_key_from_settings(json_settings)
        or "dev-secret-change-me"
    )
    app.config["SECRET_KEY"] = flask_safe_secret_key(raw_secret)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        return db.session.get(User, uid)

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(rehab_bp)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role == "patient":
                # Слэш в конце — тот же URL, что у React Router (`/patient/`)
                return redirect(url_for("patient.dashboard"))
            if current_user.role == "doctor":
                return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("auth.login"))

    @app.route("/patient")
    def patient_no_slash():
        return redirect(url_for("patient.dashboard"), code=308)

    @app.route("/doctor")
    def doctor_no_slash():
        return redirect(url_for("doctor.dashboard"), code=308)

    @app.route("/favicon.ico")
    def favicon():
        dist = Path(app.static_folder or "") / "web-dist"
        svg = dist / "favicon.svg"
        if svg.is_file():
            return send_from_directory(dist, "favicon.svg", mimetype="image/svg+xml")
        return "", 404

    with app.app_context():
        db.create_all()
        ensure_patient_profile_columns(db.engine)
        ensure_user_columns(db.engine)
        ensure_assignment_columns(db.engine)
        ensure_training_session_columns(db.engine)
        seed_exercises()
        seed_demo_doctor()

    return app
