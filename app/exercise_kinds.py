"""Классификация упражнений для UI и камеры."""

LEG_EXERCISES = frozenset(
    {
        "partial_squat",
        "knee_extension",
    }
)

# Движения в плечевом суставе (в кадре видна рука, нагрузка на плечо)
SHOULDER_EXERCISES = frozenset(
    {
        "shoulder_abduction",
        "recovery_abduction",
        "forward_raise",
        "scaption_raise",
        "arm_raise",
        "elbow_flexion",
    }
)

# Камера и детектор используют обе руки сразу (зеркально в кадре)
DUAL_ARM_EXERCISES = frozenset({"breathing_arms", "breathing_arms_slow"})

# Угол в плоскости кадра (вид сбоку) по цепочке бедро–плечо–локоть; запястье для логики не нужно.
HIP_SHOULDER_ELBOW_ANGLE_EXERCISES = frozenset(
    {
        "shoulder_abduction",
        "recovery_abduction",
        "forward_raise",
        "scaption_raise",
    }
)

# Стоять прямо лицом к камере (не в профиль); подъём вперёд — боком, как остальные плечевые
FRONTAL_STANCE_EXERCISES = frozenset()


def is_dual_arm_exercise(key: str | None) -> bool:
    return key in DUAL_ARM_EXERCISES if key else False


def is_leg_exercise(key: str | None) -> bool:
    return key in LEG_EXERCISES if key else False


def is_shoulder_exercise(key: str | None) -> bool:
    return key in SHOULDER_EXERCISES if key else False


def uses_hip_shoulder_elbow_angle_only(key: str | None) -> bool:
    return key in HIP_SHOULDER_ELBOW_ANGLE_EXERCISES if key else False


def uses_frontal_stance(key: str | None) -> bool:
    return key in FRONTAL_STANCE_EXERCISES if key else False

