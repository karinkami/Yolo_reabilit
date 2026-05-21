"""Клиническая классификация упражнений для врача: группы, подсказки по назначению, быстрые шаблоны."""

from __future__ import annotations

from typing import Any

# Порядок групп в выпадающем списке
CLINICAL_GROUPS: tuple[tuple[str, str], ...] = (
    ("shoulder_plane", "Плечо: отведение и подъёмы"),
    ("arm_elbow", "Локоть и предплечье"),
    ("breathing", "Дыхательные практики"),
    ("lower_limb", "Нижние конечности"),
)

# Ключ упражнения → метаданные для UI и API
EXERCISE_CATALOG: dict[str, dict[str, Any]] = {
    "shoulder_abduction": {
        "clinical_group": "shoulder_plane",
        "default_reps": 10,
        "frequency_hint": "1–2 раза в день, по переносимости",
        "doctor_note": "Положение: стоя. Базовое отведение в плоскости камеры. Сторона задаётся отдельно; при двустороннем назначении — на обе руки.",
    },
    "recovery_abduction": {
        "clinical_group": "shoulder_plane",
        "default_reps": 8,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Положение: стоя. Меньшая амплитуда — для ранней реабилитации или при ограничении.",
    },
    "forward_raise": {
        "clinical_group": "shoulder_plane",
        "default_reps": 10,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": (
            "Стоя боком к камере. Цикл: рука у бедра → вперёд-вверх → вниз; повтор при опускании."
        ),
    },
    "scaption_raise": {
        "clinical_group": "shoulder_plane",
        "default_reps": 10,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Положение: стоя. Плоскость лопатки (скапция) — между «вперёд» и «в сторону».",
    },
    "arm_raise": {
        "clinical_group": "shoulder_plane",
        "default_reps": 10,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Положение: стоя. Вертикальный подъём, локоть почти выпрямлен.",
    },
    "breathing_arms": {
        "clinical_group": "breathing",
        "default_reps": 6,
        "frequency_hint": "по самочувствию, 1–3 раза в день",
        "doctor_note": "Положение: стоя. Обе руки в кадре, синхронные медленные циклы. Повторы = число полных дыхательных циклов.",
    },
    "breathing_arms_slow": {
        "clinical_group": "breathing",
        "default_reps": 5,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Более медленный ритм, чем «Дыхание с руками» — подходит при необходимости снизить нагрузку и удлинить фазы.",
    },
    "partial_squat": {
        "clinical_group": "lower_limb",
        "default_reps": 8,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Стоя боком (в профиль) к камере. Частичное приседание: бедро–колено–щиколотка. В связке — правая, затем левая нога. Оцените переносимость колена.",
    },
    "elbow_flexion": {
        "clinical_group": "arm_elbow",
        "default_reps": 10,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Положение: стоя. Сгибание в локте у корпуса: плечо неподвижно, в кадре плечо–локоть–кисть.",
    },
    "knee_extension": {
        "clinical_group": "lower_limb",
        "default_reps": 10,
        "frequency_hint": "1–2 раза в день",
        "doctor_note": "Устаревшее: разгибание сидя. Для комплексов используйте упражнения стоя.",
    },
}


def catalog_for_key(key: str) -> dict[str, Any]:
    base = EXERCISE_CATALOG.get(key, {})
    return dict(base) if base else {}


# Только разные движения в списке «Одно упражнение» (без дублей дыхания/отведения/подъёмов).
DOCTOR_PICKER_EXERCISE_KEYS: frozenset[str] = frozenset(
    {
        "breathing_arms",
        "shoulder_abduction",
        "scaption_raise",
        "forward_raise",
        "elbow_flexion",
        "partial_squat",
    }
)


def exercise_visible_in_doctor_picker(key: str) -> bool:
    """Упражнения для выпадающего списка врача (белый список)."""
    return key in DOCTOR_PICKER_EXERCISE_KEYS


# Комплексы упражнений: одним действием врач назначает несколько упражнений подряд.
# Дыхательные — одна запись (обе руки синхронно); остальные — левая и правая (both_sides).
#
# Пять разных комплексов без пересечения по смыслу; внутри — только разные упражнения.
COMPLEX_CATALOG_VERSION = 4

ASSIGNMENT_COMPLEXES: list[dict[str, Any]] = [
    {
        "id": "complex_breathing",
        "label": "Комплекс: дыхание (стоя)",
        "description": "Стоя: разминка или заминка — циклы с подъёмом обеих рук, без нагрузки на суставы.",
        "items": [
            {"exercise_key": "breathing_arms", "target_reps": 6},
        ],
    },
    {
        "id": "complex_shoulder_early",
        "label": "Комплекс: руки — начальный (стоя)",
        "description": "Стоя: щадящее отведение и сгибание в локте — на обе руки.",
        "items": [
            {"exercise_key": "recovery_abduction", "target_reps": 8, "both_sides": True},
            {"exercise_key": "elbow_flexion", "target_reps": 10, "both_sides": True},
        ],
    },
    {
        "id": "complex_shoulder_full",
        "label": "Комплекс: руки — полный (стоя)",
        "description": "Стоя: отведение, подъёмы и локоть — на левую и правую руку.",
        "items": [
            {"exercise_key": "shoulder_abduction", "target_reps": 10, "both_sides": True},
            {"exercise_key": "scaption_raise", "target_reps": 10, "both_sides": True},
            {"exercise_key": "forward_raise", "target_reps": 10, "both_sides": True},
            {"exercise_key": "arm_raise", "target_reps": 10, "both_sides": True},
            {"exercise_key": "elbow_flexion", "target_reps": 10, "both_sides": True},
        ],
    },
    {
        "id": "complex_lower_limb",
        "label": "Комплекс: ноги (стоя)",
        "description": "Стоя боком: частичное приседание — на правую и левую ногу.",
        "items": [
            {"exercise_key": "partial_squat", "target_reps": 8, "both_sides": True},
        ],
    },
    {
        "id": "complex_full_body",
        "label": "Комплекс: всё тело (стоя)",
        "description": "Стоя: ноги, руки и дыхание — без упражнений сидя.",
        "items": [
            {"exercise_key": "partial_squat", "target_reps": 8, "both_sides": True},
            {"exercise_key": "shoulder_abduction", "target_reps": 10, "both_sides": True},
            {"exercise_key": "elbow_flexion", "target_reps": 10, "both_sides": True},
            {"exercise_key": "breathing_arms", "target_reps": 6},
        ],
    },
]


def _dedupe_complex_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Оставляет первое вхождение каждого exercise_key."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for it in items:
        key = str(it.get("exercise_key") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def complex_by_id(complex_id: str) -> dict[str, Any] | None:
    for c in ASSIGNMENT_COMPLEXES:
        if c["id"] == complex_id:
            return c
    return None


def _complex_item_lines(
    item: dict[str, Any], exercise_labels: dict[str, str]
) -> tuple[str, str, str]:
    """Подпись упражнения, строка деталей (повторы/стороны), короткая строка для карточки."""
    from app.exercise_kinds import is_dual_arm_exercise, is_leg_exercise

    key = str(item.get("exercise_key") or "")
    label = exercise_labels.get(key, key)
    try:
        reps = int(item.get("target_reps") or 10)
    except (TypeError, ValueError):
        reps = 10
    reps = max(1, min(50, reps))

    if is_dual_arm_exercise(key):
        detail = f"{reps} циклов, обе руки синхронно"
        short = f"{label} — {reps} цикл."
    elif item.get("both_sides"):
        if is_leg_exercise(key):
            detail = f"по {reps} повторов на левую и правую ногу"
        else:
            detail = f"по {reps} повторов на левую и правую руку"
        short = f"{label} — {reps}×2 стороны"
    else:
        # В каталоге комплексов односторонних пунктов нет; на всякий случай — как both_sides.
        if is_leg_exercise(key):
            detail = f"по {reps} повторов на левую и правую ногу"
        else:
            detail = f"по {reps} повторов на левую и правую руку"
        short = f"{label} — {reps}×2 стороны"

    return label, detail, short


def serialize_complexes(exercise_labels: dict[str, str]) -> list[dict[str, Any]]:
    """Для API: подписи упражнений из БД (exercise.key → label)."""
    out: list[dict[str, Any]] = []
    for c in ASSIGNMENT_COMPLEXES:
        items_out: list[dict[str, Any]] = []
        composition: list[str] = []
        summary_parts: list[str] = []

        for idx, it in enumerate(_dedupe_complex_items(c.get("items") or []), start=1):
            key = it["exercise_key"]
            label, detail, short = _complex_item_lines(it, exercise_labels)
            try:
                reps = int(it.get("target_reps") or 10)
            except (TypeError, ValueError):
                reps = 10

            line = f"{idx}. {label} — {detail}"
            composition.append(line)
            summary_parts.append(short)
            items_out.append(
                {
                    "exercise_key": key,
                    "exercise_label": label,
                    "target_reps": reps,
                    "both_sides": bool(it.get("both_sides")),
                    "detail": detail,
                    "short": short,
                }
            )

        out.append(
            {
                "id": c["id"],
                "label": c["label"],
                "description": c.get("description", ""),
                "items": items_out,
                "exercise_count": len(items_out),
                "composition": composition,
                "composition_text": "\n".join(composition),
                "items_summary": "; ".join(summary_parts),
            }
        )
    return out
