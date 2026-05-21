from functools import wraps

from flask import abort
from flask_login import current_user


def patient_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False) or current_user.role != "patient":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def doctor_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False) or current_user.role != "doctor":
            abort(403)
        return view(*args, **kwargs)

    return wrapped
