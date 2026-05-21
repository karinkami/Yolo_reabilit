"""Разгибание в колене сидя: от сгиба к почти прямой ноге (бедро–колено–голеностоп)."""

from __future__ import annotations

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.live_coaching import knee_extension_live, merge_tips


class KneeExtensionExercise(BaseExercise):
    def __init__(self):
        super().__init__("knee_extension")
        self.min_rep_interval = 1.25

    def detect(self, keypoints, side="left", target_reps=10):
        hip = keypoints[f"{side}_hip"]
        knee = keypoints[f"{side}_knee"]
        ankle = keypoints[f"{side}_ankle"]

        angle = angle_three_points(hip, knee, ankle)
        rate = self.angle_velocity_deg_s(angle)

        feedback = "Сядьте в профиль к камере, рабочая нога в кадре."
        correctness = "Ожидание старта"
        branch_extra: list[str] = []

        bent_threshold = 118
        extended_threshold = 152

        if not self.ready:
            if angle <= bent_threshold:
                self.ready = True
                self.phase = "down"
                feedback = "Исход: колено согнуто. Медленно разгибайте ногу до почти прямой."
                correctness = "Готово к выполнению"
            else:
                self.phase = "waiting_start"
                feedback = "Согните колено сильнее (стопа на полу или чуть впереди)."
                correctness = "Подготовка"
        else:
            if angle <= bent_threshold:
                self.phase = "down"
                feedback = "Согнутое положение — снова разгибайте ногу."
                correctness = "Хорошо"
            elif angle >= extended_threshold and self.phase == "down":
                if self.can_count_rep():
                    self.phase = "up"
                    self.reps += 1
                    feedback = f"Разгибание выполнено. Повтор {self.reps} из {target_reps}."
                    correctness = "Повтор засчитан"
                    branch_extra.append("Согните колено плавно, без резкого падения стопы.")
                else:
                    feedback = "Слишком быстро — замедлите разгибание и возврат."
                    correctness = "Слишком быстро"
            elif bent_threshold < angle < extended_threshold:
                feedback = f"Разгибание (~{round(angle)}°). Спина ровная, не откидывайтесь назад."
                correctness = "Амплитуда подходит"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["При дискомфорте в колене уменьшите амплитуду."]
        else:
            tips = merge_tips(
                knee_extension_live(angle, self.phase, self.ready, rate),
                branch_extra,
                max_items=4,
            )

        return {
            "feedback": feedback,
            "angle": angle,
            "phase": self.phase,
            "reps": self.reps,
            "correctness": correctness,
            "tips": tips,
        }
