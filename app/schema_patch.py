"""Добавление столбцов в существующую PostgreSQL БД без Alembic."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_patient_profile_columns(engine) -> None:
    try:
        insp = inspect(engine)
        tables = insp.get_table_names()
    except Exception:
        return
    if "patient_profiles" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("patient_profiles")}
    dialect = engine.dialect.name

    def add_col(name: str, ddl_sqlite: str, ddl_pg: str) -> None:
        nonlocal cols
        if name in cols:
            return
        ddl = ddl_pg if dialect == "postgresql" else ddl_sqlite
        with engine.begin() as conn:
            conn.execute(text(ddl))
        cols.add(name)

    add_col(
        "birth_date",
        "ALTER TABLE patient_profiles ADD COLUMN birth_date DATE",
        "ALTER TABLE patient_profiles ADD COLUMN birth_date DATE",
    )
    add_col(
        "comorbidities",
        'ALTER TABLE patient_profiles ADD COLUMN comorbidities TEXT DEFAULT \'\'',
        "ALTER TABLE patient_profiles ADD COLUMN comorbidities TEXT DEFAULT ''",
    )
    add_col(
        "full_name_official",
        "ALTER TABLE patient_profiles ADD COLUMN full_name_official VARCHAR(200) DEFAULT ''",
        "ALTER TABLE patient_profiles ADD COLUMN full_name_official VARCHAR(200) DEFAULT ''",
    )


def ensure_user_columns(engine) -> None:
    try:
        insp = inspect(engine)
        tables = insp.get_table_names()
    except Exception:
        return
    if "users" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "registration_pending" in cols:
        return
    dialect = engine.dialect.name
    ddl = (
        "ALTER TABLE users ADD COLUMN registration_pending BOOLEAN NOT NULL DEFAULT FALSE"
        if dialect == "postgresql"
        else "ALTER TABLE users ADD COLUMN registration_pending BOOLEAN NOT NULL DEFAULT 0"
    )
    with engine.begin() as conn:
        conn.execute(text(ddl))


def ensure_training_session_columns(engine) -> None:
    try:
        insp = inspect(engine)
        tables = insp.get_table_names()
    except Exception:
        return
    if "training_sessions" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("training_sessions")}
    dialect = engine.dialect.name

    def add_col(name: str, ddl_sqlite: str, ddl_pg: str) -> None:
        nonlocal cols
        if name in cols:
            return
        ddl = ddl_pg if dialect == "postgresql" else ddl_sqlite
        with engine.begin() as conn:
            conn.execute(text(ddl))
        cols.add(name)

    add_col("side", "ALTER TABLE training_sessions ADD COLUMN side VARCHAR(10)", "ALTER TABLE training_sessions ADD COLUMN side VARCHAR(10)")
    add_col(
        "bundle_part",
        "ALTER TABLE training_sessions ADD COLUMN bundle_part INTEGER",
        "ALTER TABLE training_sessions ADD COLUMN bundle_part INTEGER",
    )
    add_col(
        "bundle_size",
        "ALTER TABLE training_sessions ADD COLUMN bundle_size INTEGER",
        "ALTER TABLE training_sessions ADD COLUMN bundle_size INTEGER",
    )
    add_col(
        "assignment_group_id",
        "ALTER TABLE training_sessions ADD COLUMN assignment_group_id VARCHAR(36)",
        "ALTER TABLE training_sessions ADD COLUMN assignment_group_id VARCHAR(36)",
    )


def ensure_assignment_columns(engine) -> None:
    try:
        insp = inspect(engine)
        tables = insp.get_table_names()
    except Exception:
        return
    if "patient_exercise_assignments" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("patient_exercise_assignments")}
    if "assignment_group_id" in cols:
        return
    dialect = engine.dialect.name
    ddl = (
        "ALTER TABLE patient_exercise_assignments ADD COLUMN assignment_group_id VARCHAR(36)"
        if dialect == "postgresql"
        else "ALTER TABLE patient_exercise_assignments ADD COLUMN assignment_group_id VARCHAR(36)"
    )
    with engine.begin() as conn:
        conn.execute(text(ddl))
