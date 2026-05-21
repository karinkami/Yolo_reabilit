"""Подъём руки в плоскости лопатки (скапцион): угол бёдро–плечо–локоть."""

from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.live_coaching import forward_raise as live_forward_raise
from app.exercises.live_coaching import merge_tips


class ScaptionRaiseExercise(BaseExercise):
    def __init__(self):
        super().__init__("scaption_raise")
        self.min_rep_interval = 1.15

    def detect(self, keypoints, side="left", target_reps=10):
        hip = keypoints[f"{side}_hip"]
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]
        angle = angle_three_points(hip, shoulder, elbow)
        rate = self.angle_velocity_deg_s(angle)

        feedback = "Примите исходное положение: рука вдоль корпуса."
        correctness = "Ожидание старта"
        branch_extra: list[str] = []

        start_threshold = 34
        top_threshold = 74
        neutral_low = 42
        neutral_high = 68

        if not self.ready:
            if angle <= start_threshold:
                self.ready = True
                self.phase = "down"
                feedback = (
                    "Исход принят. Ведите руку по дуге «в сторону и чуть вперёд», "
                    "большой палец смотрит вверх."
                )
                correctness = "Готово к выполнению"
            else:
                self.phase = "waiting_start"
                feedback = "Опустите руку ниже вдоль бедра — нужен чистый исход."
                correctness = "Подготовка"
        else:
            if angle <= start_threshold:
                self.phase = "down"
                feedback = "Низ — следующий плавный подъём по дуге скапции."
                correctness = "Хорошо"
            elif angle >= top_threshold and self.phase == "down":
                if angle > 78:
                    feedback = "Слишком высоко — опустите руку и повторите."
                    correctness = "Слишком высоко — повтор не засчитан"
                elif self.can_count_rep():
                    self.phase = "up"
                    self.reps += 1
                    feedback = f"Верх дуги. Повтор {self.reps} из {target_reps}."
                    correctness = "Повтор засчитан"
                    branch_extra.append("Опускайте по той же траектории, без наклона корпуса назад.")
                else:
                    feedback = "Цикл слишком быстрый — выдержите паузу внизу."
                    correctness = "Слишком быстро"
            elif neutral_low <= angle <= neutral_high:
                feedback = f"Середина дуги (~{round(angle)}°). Локоть чуть в сторону, не заводите за спину."
                correctness = "Траектория хорошая"
            elif angle > 92:
                feedback = "Слишком высоко или слишком «чисто в сторону» — смягчите дугу в сторону лба."
                correctness = "Скорректируйте амплитуду"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Хорошая работа по плоскости лопатки."]
        else:
            tips = merge_tips(
                live_forward_raise(
                    angle,
                    self.phase,
                    self.ready,
                    rate,
                    start_thr=start_threshold,
                    top_thr=top_threshold,
                    neutral_low=neutral_low,
                    neutral_high=neutral_high,
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
