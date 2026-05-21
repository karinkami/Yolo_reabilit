"""Групповые назначения (обе руки): склейка для UI пациента и врача."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.exercise_kinds import is_dual_arm_exercise, is_leg_exercise
from app.side_labels import side_imperative, side_label_full, side_now_short


def _safe_exercise(assignment: Any):
    return getattr(assignment, "exercise", None)


def _max_created_at(rows: list[Any]) -> datetime:
    times = [r.created_at for r in rows if getattr(r, "created_at", None) is not None]
    return max(times) if times else datetime.utcnow()


def _side_rank(side: str) -> int:
    """Порядок в связке «обе руки»: сначала правая, затем левая (и для очереди, и для фокуса модели)."""
    return 0 if side == "right" else 1


def rehab_select_options(assignments: list[Any]) -> list[dict[str, Any]]:
    """Варианты для тренировки: одиночные строки для плеча и связка правая+левая (порядок очереди)."""
    by_group: dict[str, list[Any]] = defaultdict(list)
    singles: list[Any] = []
    for a in assignments:
        gid = getattr(a, "assignment_group_id", None)
        if gid:
            by_group[str(gid)].append(a)
        else:
            singles.append(a)

    bundles: list[dict[str, Any]] = []
    for gid, rows in by_group.items():
        rows = sorted(rows, key=lambda x: _side_rank(str(x.side)))
        ex_ids = {r.exercise_id for r in rows}
        reps = {r.target_reps for r in rows}
        if (
            len(rows) == 2
            and len(ex_ids) == 1
            and len(reps) == 1
            and rows[0].side != rows[1].side
        ):
            bundles.append({"kind": "bundle", "rows": rows})
        else:
            singles.extend(rows)

    lone: list[dict[str, Any]] = [{"kind": "single", "rows": [r]} for r in singles]

    def newest(opt: dict[str, Any]) -> Any:
        times = [x.created_at for x in opt["rows"] if getattr(x, "created_at", None) is not None]
        return max(times) if times else datetime.min

    options = bundles + lone
    options.sort(key=newest, reverse=True)
    return options


def _assignments_payload(rows: list[Any], exercise_key: str) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        side = str(r.side)
        out.append(
            {
                "id": r.id,
                "side": side,
                "target_reps": int(r.target_reps),
                "side_label": side_label_full(side, exercise_key),
                "side_imperative": side_imperative(side, exercise_key),
            }
        )
    return out


def enrich_option_for_template(opt: dict[str, Any], patient_id: int | None = None) -> dict[str, Any]:
    rows = opt["rows"]
    primary = rows[0]
    ex = primary.exercise
    key = ex.key
    tr = int(primary.target_reps)
    assignments_payload = _assignments_payload(rows, key)
    is_bundle = opt["kind"] == "bundle" and len(rows) > 1
    label_base = str(ex.label)
    dual_motion = is_dual_arm_exercise(key)

    if is_bundle:
        if dual_motion:
            label_side = "обе руки одновременно, {} медленных циклов".format(tr)
            short_label = "{} • обе руки разом × {}".format(label_base, tr)
        elif key == "partial_squat":
            label_side = "два подхода боком — по {} повторений в каждом".format(tr)
            short_label = f"{label_base} • боком ×2 × {tr}"
        elif is_leg_exercise(key):
            label_side = "сначала правая нога, затем левая — по {} повторений каждая".format(tr)
            short_label = f"{label_base} • правая → левая × {tr}"
        else:
            label_side = "сначала правая рука, затем левая — по {} повторений каждая".format(tr)
            short_label = f"{label_base} • правая → левая × {tr}"
    elif dual_motion:
        label_side = "обе руки одновременно, {} медленных циклов".format(tr)
        short_label = "{} • обе руки разом × {}".format(label_base, tr)
    else:
        if key == "partial_squat":
            label_side = "стоя боком, {} повтор.".format(tr)
        else:
            side_lr = "левая" if primary.side == "left" else "правая"
            limb = "нога" if is_leg_exercise(key) else "рука"
            label_side = "{} {}, {} повтор.".format(side_lr, limb, tr)
        short_label = f"{label_base} • {label_side}"

    current_side = str(primary.side)
    bundle_progress: dict[str, int | str] = {}
    if is_bundle and patient_id is not None:
        from app.assignment_completion import bundle_progress_for_rows

        bundle_progress = bundle_progress_for_rows(int(patient_id), list(rows))
        prog = str(bundle_progress.get("progress_label") or "")
        if prog and prog not in short_label:
            short_label = f"{label_base} • {prog}"
            label_side = f"{label_side} ({prog})"

    queue_index = int(bundle_progress.get("queue_index", 0)) if bundle_progress else 0
    active_row = rows[min(queue_index, len(rows) - 1)] if rows else primary
    current_side = str(active_row.side)

    return {
        "kind": opt["kind"],
        "assignments_payload": assignments_payload,
        "primary_id": primary.id,
        "exercise_key": key,
        "is_leg": is_leg_exercise(key),
        "dual_breathing": dual_motion,
        "target_reps": tr,
        "label_line": "{} — {}".format(label_base, label_side),
        "short_label": short_label,
        "assignment_count": len(rows),
        "bundle_mode": bool(is_bundle),
        "sides_total": int(bundle_progress.get("sides_total", len(rows) if is_bundle else 1)),
        "sides_done": int(bundle_progress.get("sides_done", 0)),
        "bundle_progress_label": str(bundle_progress.get("progress_label") or ""),
        "next_side_label": str(bundle_progress.get("next_side_label") or ""),
        "recommended_queue_index": queue_index,
        "current_side": current_side,
        "current_side_label": side_now_short(current_side, key),
        "bundle_hint": (
            "Сначала правая, затем левая"
            if is_bundle and not dual_motion and not is_leg_exercise(key)
            else (
                "Сначала стоя боком (правая), затем боком (левая)"
                if is_bundle and key == "partial_squat"
                else (
                    "Сначала правая нога, затем левая"
                    if is_bundle and is_leg_exercise(key)
                    else ""
                )
            )
        ),
    }


def assignments_for_doctor_display(
    assignments: list[Any], patient_id: int | None = None
) -> list[dict[str, Any]]:
    """Строки для списка на странице врача."""

    by_group: dict[str, list[Any]] = defaultdict(list)
    base_singles: list[Any] = []
    for a in assignments:
        gid = getattr(a, "assignment_group_id", None)
        if gid:
            by_group[str(gid)].append(a)
        else:
            base_singles.append(a)

    paired_ids: set[int] = set()
    pairs: list[dict[str, Any]] = []

    for gid, rows in by_group.items():
        rows = sorted(rows, key=lambda x: _side_rank(str(x.side)))
        ok = (
            len(rows) == 2
            and rows[0].exercise_id == rows[1].exercise_id
            and rows[0].target_reps == rows[1].target_reps
            and rows[0].side != rows[1].side
        )
        if ok:
            ex = _safe_exercise(rows[0])
            if ex is None:
                base_singles.extend(rows)
                continue
            k = ex.key
            if k == "partial_squat":
                detail = "два подхода боком • по {} повт.".format(rows[0].target_reps)
            else:
                limb = "нога" if is_leg_exercise(k) else "рука"
                detail = "сначала правая {}, затем левая {} • по {} повт.".format(
                    limb,
                    limb,
                    rows[0].target_reps,
                )
            if patient_id is not None:
                from app.assignment_completion import bundle_progress_for_rows

                prog = bundle_progress_for_rows(int(patient_id), list(rows))
                detail = f"{detail} • выполнено {prog.get('progress_label', '0/2')}"
            pairs.append(
                {
                    "type": "pair",
                    "group_id": gid,
                    "ids": [rows[0].id, rows[1].id],
                    "created_at": _max_created_at(rows),
                    "exercise_label": ex.label,
                    "detail": detail,
                }
            )
            paired_ids.update(r.id for r in rows)
        else:
            base_singles.extend(rows)

    singleton_lines: list[dict[str, Any]] = []
    for a in base_singles:
        if a.id in paired_ids:
            continue
        ex = _safe_exercise(a)
        if ex is None:
            continue
        k = ex.key
        if is_dual_arm_exercise(k):
            detail = "обе руки синхронно, {} цикл.".format(a.target_reps)
        else:
            if k == "partial_squat":
                detail = "стоя боком, {} повт.".format(a.target_reps)
            else:
                side_lr = "левая" if a.side == "left" else "правая"
                limb = "нога" if is_leg_exercise(k) else "рука"
                detail = "{} {}, {} повт.".format(side_lr, limb, a.target_reps)
        singleton_lines.append(
            {
                "type": "single",
                "ids": [a.id],
                "created_at": a.created_at or datetime.utcnow(),
                "exercise_label": ex.label,
                "detail": detail,
            }
        )

    out = pairs + singleton_lines
    out.sort(key=lambda row: row.get("created_at") or datetime.min, reverse=True)
    return out
