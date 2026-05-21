"""Подписи стороны для назначений врача (рука/нога)."""



from __future__ import annotations



from app.exercise_kinds import (

    is_dual_arm_exercise,

    is_leg_exercise,


)





def _is_partial_squat(exercise_key: str | None) -> bool:

    return exercise_key == "partial_squat"





def side_limb_word(exercise_key: str | None) -> str:

    return "нога" if is_leg_exercise(exercise_key) else "рука"





def side_limb_accusative(exercise_key: str | None) -> str:

    return "ногу" if is_leg_exercise(exercise_key) else "руку"





def side_adjective(side: str) -> str:

    return "левая" if side == "left" else "правая"





def side_label_full(side: str, exercise_key: str | None) -> str:

    if _is_partial_squat(exercise_key):

        return "Стоя боком"

    return f"{side_adjective(side).capitalize()} {side_limb_word(exercise_key)}"





def side_instrumental_phrase(side: str, exercise_key: str | None) -> str:

    if side == "left":

        return "левой рукой" if not is_leg_exercise(exercise_key) else "левой ногой"

    return "правой рукой" if not is_leg_exercise(exercise_key) else "правой ногой"





def side_imperative(side: str, exercise_key: str | None) -> str:

    if _is_partial_squat(exercise_key):

        return "Встаньте боком к камере"

    limb = side_limb_accusative(exercise_key)

    if side == "left":

        return f"Встаньте боком к камере. Используйте левую {limb}"

    return f"Встаньте боком к камере. Используйте правую {limb}"





def side_prepare_feedback(side: str, exercise_key: str | None) -> str:

    if is_dual_arm_exercise(exercise_key):

        return "Подготовьтесь: встаньте боком к камере, двигайте обе руки синхронно."

    if _is_partial_squat(exercise_key):

        return (

            "Встаньте боком к камере — рабочая нога ближе к объективу. "

            "Подготовьтесь к приседанию: бедро, колено и щиколотка в кадре."

        )

    instr = side_instrumental_phrase(side, exercise_key)

    return (

        f"Встаньте боком к камере, работайте {instr}. "

        "Подготовьтесь к выполнению упражнения."

    )





def side_now_short(side: str, exercise_key: str | None) -> str:

    if is_dual_arm_exercise(exercise_key):

        return "Обе руки"

    if _is_partial_squat(exercise_key):

        return "Стоя боком"

    return side_label_full(side, exercise_key)

