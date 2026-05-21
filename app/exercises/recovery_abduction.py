from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.live_coaching import abduction_side, merge_tips


class RecoveryAbductionExercise(BaseExercise):
    """Отведение в сторону с малой амплитудой."""

    def __init__(self):
        super().__init__("recovery_abduction")
        self.min_rep_interval = 1.35

    def detect(self, keypoints, side="left", target_reps=10):
        hip = keypoints[f"{side}_hip"]
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]
        angle = angle_three_points(hip, shoulder, elbow)
        rate = self.angle_velocity_deg_s(angle)

        feedback = "Рука вдоль бедра."
        correctness = "Ожидание старта"
        branch_extra: list[str] = []

        start_threshold = 30
        top_threshold = 55
        neutral_low = 35
        neutral_high = 52

        if not self.ready:
            if angle <= start_threshold:
                self.ready = True
                self.phase = "down"
                feedback = "Короткое отведение в сторону и возврат — только в комфорте."
                correctness = "Готово к выполнению"
            else:
                self.phase = "waiting_start"
                feedback = "Опустите руку ниже для исхода."
                correctness = "Подготовка"
        else:
            if angle <= start_threshold:
                self.phase = "down"
                feedback = "Исход — лёгкий отвод в сторону."
                correctness = "Хорошо"
            elif angle >= top_threshold and self.phase == "down":
                if angle > 58:
                    feedback = "Слишком широко для этого режима — уменьшите амплитуду."
                    correctness = "Слишком высоко — повтор не засчитан"
                elif self.can_count_rep():
                    self.phase = "up"
                    self.reps += 1
                    feedback = f"Малая верхняя точка. Повтор {self.reps} из {target_reps}."
                    correctness = "Повтор засчитан"
                    branch_extra.append("Опускайте с тем же мягким темпом.")
                else:
                    feedback = "Ускорили — замедлите малую амплитуду."
                    correctness = "Слишком быстро"
            elif neutral_low <= angle <= neutral_high:
                feedback = f"В целевой зоне (~{round(angle)}°). Не наклоняйтесь в сторону."
                correctness = "Норма"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Хороший контроль в малой амплитуде."]
        else:
            tips = merge_tips(
                abduction_side(
                    angle,
                    self.phase,
                    self.ready,
                    rate,
                    start_thr=start_threshold,
                    top_thr=top_threshold,
                    neutral_low=neutral_low,
                    neutral_high=neutral_high,
                    high_warn=None,
                ),
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
