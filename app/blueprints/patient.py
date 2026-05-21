from flask import Blueprint, redirect, url_for
from flask_login import login_required

from app.roles import patient_required
from app.spa_utils import send_web_spa

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")


@patient_bp.route("/")
@login_required
@patient_required
def dashboard():
    return send_web_spa()


@patient_bp.route("/stats")
@login_required
@patient_required
def stats():
    return send_web_spa()


@patient_bp.route("/history")
@login_required
@patient_required
def history():
    return redirect(url_for("patient.stats"), code=302)
