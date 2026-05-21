"""Медленный подъём обеих рук вместе — в такт спокойному дыханию (вдох вверх / выдох вниз)."""

from __future__ import annotations

import math

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.live_coaching import breathing_dual_moment, merge_tips

# Пороги по высоте кисти относительно плеча (нормировано на ширину плеч)
LIFT_DOWN = 0.12
LIFT_UP = 0.40
LIFT_RESET = 0.15

# Для подсказок и UI — как «угол» плечо–локоть–кисть
ANGLE_AT_DOWN = 150.0
ANGLE_AT_UP = 118.0
ANGLE_SPAN = ANGLE_AT_DOWN - ANGLE_AT_UP


def _shoulder_span(points: dict) -> float:
    ls = points["left_shoulder"]
    rs = points["right_shoulder"]
    return max(55.0, math.hypot(ls[0] - rs[0], ls[1] - rs[1]))


def _lift_norm(points: dict, side: str) -> float:
    sh = points[f"{side}_shoulder"]
    wr = points[f"{side}_wrist"]
    span = _shoulder_span(points)
    return (sh[1] - wr[1]) / span


def _lift_to_display_angle(lift_norm: float) -> float:
    return ANGLE_AT_DOWN - lift_norm * ANGLE_SPAN


def _dual_mode(points: dict) -> bool:
    return (
        "left_shoulder" in points
        and "right_shoulder" in points
        and "left_wrist" in points
        and "right_wrist" in points
    )


class BreathingArmsExercise(BaseExercise):
    def __init__(self):
        super().__init__("breathing_arms")
        self.min_rep_interval = 2.4

    def detect(self, keypoints: dict, side: str = "left", target_reps: int = 10):
        if _dual_mode(keypoints):
            return self._detect_dual(keypoints, target_reps)
        return self._detect_single_side(keypoints, side, target_reps)

    def _detect_dual(self, keypoints: dict, target_reps: int) -> dict:
        lift_left = _lift_norm(keypoints, "left")
        lift_right = _lift_norm(keypoints, "right")
        lift_avg = (lift_left + lift_right) / 2.0
        asymmetry = abs(lift_left - lift_right)

        angle_left = _lift_to_display_angle(lift_left)
        angle_right = _lift_to_display_angle(lift_right)
        angle_avg = (angle_left + angle_right) / 2.0
        rate = self.angle_velocity_deg_s(angle_avg)

        asym_hard = 0.22
        asym_soft = 0.14

        breath_hint = [
            "Вдох через нос на подъёме, выдох на опускании — плечи не к ушам.",
        ]

        feedback = (
            "В кадре поднимите обе руки до уровня плеч и ниже — медленно и симметрично."
        )
        correctness = "Готовьтесь стартовать обеими руками"
        tips_addon: list[str] = []

        if asymmetry > asym_hard:
            return {
                "feedback": (
                    "Руки на разной высоте — выровняйте: двигайте обе симметрично."
                ),
                "angle": angle_avg,
                "phase": self.phase,
                "reps": self.reps,
                "correctness": "Нужно синхронно",
                "tips": [
                    "Смотрите в кадр: оба локтя на одной высоте.",
                    "Поднимите и опустите на пару сантиметров, чтобы поймать ритм.",
                ],
            }

        sym_note = asymmetry > asym_soft

        if not self.ready:
            if lift_avg <= LIFT_DOWN:
                self.ready = True
                self.phase = "down"
                feedback = (
                    "Исход есть. На вдохе обе руки вверх, на выдохе — мягко вниз, одновременно."
                )
                correctness = "Стартуйте медленный цикл"
                if sym_note:
                    correctness = "Чуть симметричнее"
                    feedback += " Слегка подровняйте высоту кистей."
            else:
                self.phase = "waiting_start"
                feedback = (
                    "Опустите обе руки ниже: плечи, локти и кисти в кадре, кисти ниже плеч."
                )
                correctness = "Исходное положение"
                tips_addon.append("Отойдите чуть назад, если руки не помещаются в кадр.")
        else:
            if lift_avg <= LIFT_RESET:
                self.phase = "down"
                feedback = "Фаза выдоха — опускайте обе руки плавно."
                correctness = "Выдох, обе опускаются"
            elif lift_avg >= LIFT_UP and self.phase == "down":
                if self.can_count_rep() and asymmetry <= asym_soft:
                    self.phase = "up"
                    self.reps += 1
                    feedback = (
                        f"Цикл {self.reps} из {target_reps}. Следующий выдох — плавно вниз."
                    )
                    correctness = "Цикл выполнен"
                elif not self.can_count_rep():
                    feedback = (
                        "Слишком быстро между циклами. Пауза 2–3 секунды, дышите между движениями."
                    )
                    correctness = "Замедлите темп"
                else:
                    feedback = "Выровняйте руки по высоте — тогда повтор засчитается."
                    correctness = "Симметрия"
            elif lift_avg >= LIFT_UP * 0.65:
                feedback = (
                    f"Подъём (~{round(angle_avg)}°). Поднимите кисти чуть выше плеч для полного цикла."
                )
                correctness = "Вдох, подъём"
            else:
                feedback = "Продолжайте обеими руками в одном темпе."
                correctness = "Выполняете"

        if self.reps >= target_reps:
            feedback = f"Готово: {self.reps} из {target_reps} циклов."
            correctness = "Упражнение завершено"
            tips = ["Можно отдохнуть. Сохраняйте спокойный темп."]
        else:
            tips = merge_tips(
                breathing_dual_moment(
                    angle_avg,
                    angle_left,
                    angle_right,
                    self.phase,
                    self.ready,
                    rate,
                    start_thr=ANGLE_AT_DOWN,
                    top_thr=ANGLE_AT_UP,
                    neutral_low=ANGLE_AT_UP + 6,
                    neutral_high=ANGLE_AT_DOWN - 2,
                    asym_soft=asym_soft * ANGLE_SPAN,
                ),
                breath_hint,
                tips_addon,
                max_items=4,
            )

        return {
            "feedback": feedback,
            "angle": angle_avg,
            "phase": self.phase,
            "reps": self.reps,
            "correctness": correctness,
            "tips": tips,
        }

    def _detect_single_side(
        self,
        keypoints: dict,
        side: str,
        target_reps: int,
    ) -> dict:
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]
        wrist = keypoints[f"{side}_wrist"]
        angle = angle_three_points(shoulder, elbow, wrist)

        feedback = (
            "Нужны обе руки в кадре: отойдите так, чтобы видны плечи, локти и кисти слева и справа."
        )
        correctness = "Режим для двух рук"
        tips = [
            "Можно стоять боком или четвертью поворотом к камере.",
            "Поднимайте обе руки синхронно.",
        ]

        return {
            "feedback": feedback,
            "angle": angle,
            "phase": "waiting_start",
            "reps": self.reps,
            "correctness": correctness,
            "tips": tips,
        }
