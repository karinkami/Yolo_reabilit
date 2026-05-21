"""Подъём руки вверх: угол плечо–локоть–кисть, как присед — от исхода."""

from __future__ import annotations

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points

# Рука внизу — большой угол; вверху — меньше; засчёт при возврате вниз
DROP_UP = 14
RETURN_DROP = 8
MIN_UP_FRAMES = 3
REST_MARGIN = 5


class ArmRaiseExercise(BaseExercise):
    def __init__(self):
        super().__init__("arm_raise")
        self.min_rep_interval = 0.55
        self._high_angle: float | None = None
        self._was_up = False
        self._up_frames = 0
        self._warmup = 0

    def reset(self):
        super().reset()
        self._high_angle = None
        self._was_up = False
        self._up_frames = 0
        self._warmup = 0

    def detect(self, keypoints, side="left", target_reps=10):
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]
        wrist = keypoints[f"{side}_wrist"]
        angle = angle_three_points(shoulder, elbow, wrist)

        if self._high_angle is None:
            self._high_angle = angle
        drop = self._high_angle - angle

        if drop < REST_MARGIN:
            self._high_angle = max(self._high_angle, angle)
            self._up_frames = 0

        self._warmup += 1

        if self._warmup < 12:
            self.phase = "waiting_start"
            feedback = f"Рука внизу вдоль тела (~{round(angle)}°)…"
            correctness = "Подготовка"
        elif not self.ready:
            self.ready = True
            feedback = "Готово. Поднимите руку вверх и опустите — повтор на опускании."
            correctness = "Готово к выполнению"
        elif drop >= DROP_UP:
            self._up_frames += 1
            if self._up_frames >= MIN_UP_FRAMES:
                self._was_up = True
            self.phase = "up"
            feedback = f"Вверх (~{round(angle)}°). Опустите руку."
            correctness = "Вверх"
        elif self._was_up and drop <= RETURN_DROP and self.can_count_rep():
            self.reps += 1
            self._was_up = False
            self._up_frames = 0
            self.phase = "down"
            feedback = f"Повтор {self.reps} из {target_reps}."
            correctness = "Повтор засчитан"
        else:
            self.phase = "down"
            if self._was_up:
                feedback = f"Опускайте руку вниз (~{round(angle)}°)."
                correctness = "Опускайте"
            else:
                feedback = f"Рука внизу (~{round(angle)}°). Поднимите вверх (≈{DROP_UP}°)."
                correctness = "Поднимите руку"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Упражнение выполнено."]
        else:
            tips = [
                "Боком к камере: плечо, локоть, кисть в кадре.",
                f"Подъём ~{DROP_UP}° от положения «рука внизу», затем опускание.",
            ]

        return {
            "feedback": feedback,
            "angle": angle,
            "phase": self.phase,
            "reps": self.reps,
            "correctness": correctness,
            "tips": tips,
        }
