"""Частичное приседание боком: стойка → сгибание → выпрямление — один повтор."""

from __future__ import annotations

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.squat_thresholds import (
    ANGLE_EMA_ALPHA,
    BENT_DROP,
    MIN_BENT_FRAMES,
    MIN_DEEP_DROP,
    RETURN_DROP,
    STAND_MARGIN,
    STAND_SETTLE_FRAMES,
)


class PartialSquatExercise(BaseExercise):
    def __init__(self):
        super().__init__("partial_squat")
        self.min_rep_interval = 0.65
        self._angle_ema: float | None = None
        self._stand_angle: float | None = None
        self._stand_settle = 0
        self._was_bent = False
        self._bent_frames = 0
        self._deepest_drop = 0.0
        self._warmup = 0

    def reset(self):
        super().reset()
        self._angle_ema = None
        self._stand_angle = None
        self._stand_settle = 0
        self._was_bent = False
        self._bent_frames = 0
        self._deepest_drop = 0.0
        self._warmup = 0

    def _smooth_angle(self, raw: float) -> float:
        if self._angle_ema is None:
            self._angle_ema = raw
        else:
            a = ANGLE_EMA_ALPHA
            self._angle_ema = a * raw + (1.0 - a) * self._angle_ema
        return self._angle_ema

    def detect(self, keypoints, side="left", target_reps=10):
        hip = keypoints[f"{side}_hip"]
        knee = keypoints[f"{side}_knee"]
        ankle = keypoints[f"{side}_ankle"]
        raw = angle_three_points(hip, knee, ankle)
        angle = self._smooth_angle(raw)

        if self._stand_angle is None:
            self._stand_angle = angle
        drop = self._stand_angle - angle

        if drop <= STAND_MARGIN:
            self._stand_settle += 1
            if self._stand_settle >= STAND_SETTLE_FRAMES:
                self._stand_angle = max(self._stand_angle, angle)
        else:
            self._stand_settle = 0
            self._deepest_drop = max(self._deepest_drop, drop)

        if drop >= BENT_DROP:
            self._bent_frames += 1
            if self._bent_frames >= MIN_BENT_FRAMES:
                self._was_bent = True
        elif drop < BENT_DROP - 4:
            self._bent_frames = 0

        if (
            self.ready
            and self._warmup >= 15
            and self._was_bent
            and drop <= RETURN_DROP
            and self._deepest_drop >= MIN_DEEP_DROP
            and self.can_count_rep()
        ):
            self.reps += 1
            self._was_bent = False
            self._bent_frames = 0
            self._deepest_drop = 0.0
            self._stand_angle = angle
            self._stand_settle = STAND_SETTLE_FRAMES

        self._warmup += 1

        if self._warmup < 15:
            self.phase = "waiting_start"
            feedback = f"Встаньте боком, выпрямите колено (~{round(angle)}°)…"
            correctness = "Подготовка"
        elif not self.ready:
            self.ready = True
            feedback = (
                "Готово. Присядьте так, чтобы колено заметно согнулось, "
                "затем полностью выпрямитесь — тогда засчитается повтор."
            )
            correctness = "Готово к приседанию"
        elif drop >= BENT_DROP and self._was_bent:
            self.phase = "down"
            feedback = f"Вниз (~{round(angle)}°, −{round(drop)}°). Поднимитесь в стойку."
            correctness = "Вниз"
        elif self._was_bent and drop > RETURN_DROP:
            self.phase = "up"
            feedback = (
                f"Поднимитесь (~{round(angle)}°, до стойки ≈{RETURN_DROP}°). "
                f"Глубина −{round(self._deepest_drop)}°."
            )
            correctness = "Поднимайтесь"
        elif drop >= BENT_DROP:
            self.phase = "down"
            feedback = f"Глубже (~{round(angle)}°, −{round(drop)}°), нужно ≈{BENT_DROP}°."
            correctness = "Согнитесь глубже"
        else:
            self.phase = "up"
            feedback = f"Стоя (~{round(angle)}°). Присядьте (≈{BENT_DROP}° от стойки)."
            correctness = "Присядьтесь"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Упражнение выполнено."]
        else:
            tips = [
                "Стоя боком: бедро, колено и щиколотка рабочей ноги в кадре.",
                f"Присед ~{BENT_DROP}° и выпрямление почти в стойку (~{RETURN_DROP}°) — один повтор.",
            ]

        return {
            "feedback": feedback,
            "angle": round(angle, 1),
            "phase": self.phase,
            "reps": self.reps,
            "correctness": correctness,
            "tips": tips,
        }
