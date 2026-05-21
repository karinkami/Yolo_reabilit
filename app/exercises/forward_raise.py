"""Подъём руки вперёд боком к камере: от исхода внизу, подъём вперёд-вверх, опускание."""

from __future__ import annotations

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points

# Подъём руки от «рука внизу» (град.), засчёт при опускании
LIFT_RISE = 12
RETURN_RISE = 6
MIN_UP_FRAMES = 3
REST_MARGIN = 4


class ForwardRaiseExercise(BaseExercise):
    def __init__(self):
        super().__init__("forward_raise")
        self.min_rep_interval = 0.55
        self._low_angle: float | None = None
        self._was_up = False
        self._up_frames = 0
        self._warmup = 0

    def reset(self):
        super().reset()
        self._low_angle = None
        self._was_up = False
        self._up_frames = 0
        self._warmup = 0

    def detect(self, keypoints, side="left", target_reps=10):
        hip = keypoints[f"{side}_hip"]
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]
        angle = angle_three_points(hip, shoulder, elbow)

        if self._low_angle is None:
            self._low_angle = angle
        rise = angle - self._low_angle

        if rise < REST_MARGIN:
            self._low_angle = min(self._low_angle, angle)
            self._up_frames = 0

        self._warmup += 1

        if self._warmup < 12:
            self.phase = "waiting_start"
            feedback = (
                f"Встаньте боком к камере, рука вдоль бедра (~{round(angle)}°). "
                "Рабочая сторона ближе к объективу."
            )
            correctness = "Подготовка"
        elif not self.ready:
            self.ready = True
            feedback = (
                "Готово. Поднимите руку вперёд-вверх от бедра, затем опустите вниз — "
                "повтор засчитается при опускании."
            )
            correctness = "Готово к выполнению"
        elif rise >= LIFT_RISE:
            self._up_frames += 1
            if self._up_frames >= MIN_UP_FRAMES:
                self._was_up = True
            self.phase = "up"
            feedback = (
                f"Подъём вперёд (~{round(angle)}°, +{round(rise)}°). "
                "Опустите руку вниз к бедру."
            )
            correctness = "Вверх"
        elif self._was_up and rise <= RETURN_RISE and self.can_count_rep():
            self.reps += 1
            self._was_up = False
            self._up_frames = 0
            self.phase = "down"
            feedback = f"Повтор {self.reps} из {target_reps} засчитан (рука внизу)."
            correctness = "Повтор засчитан"
        else:
            self.phase = "down"
            if self._was_up:
                feedback = f"Опускайте руку вниз к бедру (~{round(angle)}°), боком к камере."
                correctness = "Опускайте"
            else:
                feedback = (
                    f"Рука внизу (~{round(angle)}°). Поднимите вперёд-вверх "
                    f"(не в сторону), нужно ≈{LIFT_RISE}° от исхода."
                )
                correctness = "Поднимите вперёд"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Упражнение выполнено. Можно отдохнуть."]
        else:
            tips = [
                "Стоя боком к камере: плечо, локоть и кисть рабочей руки в кадре.",
                "Движение: вниз у бедра → вперёд-вверх → вниз; не отводите руку в сторону от корпуса.",
                f"Повтор засчитывается, когда рука снова опущена после подъёма (~{RETURN_RISE}° к исходу).",
            ]

        return {
            "feedback": feedback,
            "angle": angle,
            "phase": self.phase,
            "reps": self.reps,
            "correctness": correctness,
            "tips": tips,
        }
