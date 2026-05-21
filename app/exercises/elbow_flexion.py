"""Сгибание в локте: предплечье к плечу, плечо неподвижно (угол плечо–локоть–кисть)."""

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.live_coaching import merge_tips, vertical_arm_sagittal


class ElbowFlexionExercise(BaseExercise):
    def __init__(self):
        super().__init__("elbow_flexion")
        self.min_rep_interval = 1.2

    def detect(self, keypoints, side="left", target_reps=10):
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]
        wrist = keypoints[f"{side}_wrist"]

        angle = angle_three_points(shoulder, elbow, wrist)
        rate = self.angle_velocity_deg_s(angle)

        feedback = "Рука вдоль корпуса, локоть прижат к боку."
        correctness = "Ожидание старта"
        branch_extra: list[str] = []

        start_threshold = 158
        top_threshold = 78
        neutral_low = 88
        neutral_high = 150

        if not self.ready:
            if angle >= start_threshold:
                self.ready = True
                self.phase = "down"
                feedback = "Исход принят. Сгибайте локоть, подводя кисть к плечу; плечо не отводите."
                correctness = "Готово к выполнению"
            else:
                self.phase = "waiting_start"
                feedback = "Выпрямите руку вниз вдоль бедра — локоть у бока."
                correctness = "Подготовка"
        else:
            if angle >= start_threshold:
                self.phase = "down"
                feedback = "Низ — следующее сгибание в локте."
                correctness = "Хорошо"
            elif angle <= top_threshold and self.phase == "down":
                if self.can_count_rep():
                    self.phase = "up"
                    self.reps += 1
                    feedback = f"Сгибание выполнено. Повтор {self.reps} из {target_reps}."
                    correctness = "Повтор засчитан"
                    branch_extra.append("Разгибайте локоть плавно, не раскачивайте корпус.")
                else:
                    feedback = "Слишком быстро — замедлите сгибание и разгибание."
                    correctness = "Слишком быстро"
            elif neutral_low <= angle <= neutral_high:
                feedback = f"Середина дуги (~{round(angle)}°). Локоть у бока, плечо не поднимайте."
                correctness = "Амплитуда нормальная"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Хороший контроль локтя."]
        else:
            tips = merge_tips(
                vertical_arm_sagittal(
                    angle,
                    self.phase,
                    self.ready,
                    rate,
                    start_thr=start_threshold,
                    top_thr=top_threshold,
                    neutral_low=neutral_low,
                    neutral_high=neutral_high,
                ),
                ["Не отводите плечо от корпуса — работает только предплечье."],
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
