from app.exercises.base import BaseExercise
from app.exercises.geometry import angle_three_points
from app.exercises.live_coaching import abduction_side, merge_tips


class ShoulderAbductionExercise(BaseExercise):
    def __init__(self):
        super().__init__("shoulder_abduction")
        self.min_rep_interval = 0.95

    def detect(self, keypoints, side="left", target_reps=10):
        hip = keypoints[f"{side}_hip"]
        shoulder = keypoints[f"{side}_shoulder"]
        elbow = keypoints[f"{side}_elbow"]

        angle = angle_three_points(hip, shoulder, elbow)
        rate = self.angle_velocity_deg_s(angle)

        feedback = "Примите исходное положение."
        correctness = "Ожидание старта"
        branch_extra: list[str] = []

        # В профиле угол бедро–плечо–локоть растёт меньше, чем «в лицо» — пороги ниже.
        start_threshold = 30
        return_down_threshold = 38
        top_threshold = 68
        neutral_low = 32
        neutral_high = 66
        too_high_block = 84

        if not self.ready:
            if angle <= start_threshold:
                self.ready = True
                self.phase = "down"
                feedback = "Исход принят. Медленно отводите руку в сторону и возвращайте вниз."
                correctness = "Готово к выполнению"
            else:
                self.phase = "waiting_start"
                feedback = "Опустите руку вдоль бедра для исхода."
                correctness = "Подготовка"
        else:
            if angle <= return_down_threshold:
                self.phase = "down"
                if angle <= start_threshold + 2:
                    feedback = "Низ — следующий отвод в сторону."
                    correctness = "Хорошо"
                else:
                    feedback = "Чуть ниже — почти готово к следующему отведению."
                    correctness = "Опускайте до исхода"

            elif angle >= top_threshold and self.phase == "down":
                if angle > too_high_block:
                    feedback = (
                        f"Слишком высоко (~{round(angle)}°). Опустите руку и повторите в комфортной амплитуде."
                    )
                    correctness = "Слишком высоко — повтор не засчитан"
                    branch_extra.append("Верх — без форсирования высоты.")
                elif self.can_count_rep():
                    self.phase = "up"
                    self.reps += 1
                    feedback = f"Верх отведения (~{round(angle)}°). Повтор {self.reps} из {target_reps}."
                    correctness = "Повтор засчитан"
                    branch_extra.append("Опустите руку вниз до исхода перед следующим отводом.")
                else:
                    feedback = "Слишком быстро — пауза внизу, затем снова вверх."
                    correctness = "Слишком быстро"
                    branch_extra.append("Между повторами выдержите 1–2 секунды внизу.")

            elif self.phase == "up" and angle >= top_threshold - 4:
                feedback = (
                    f"Сначала опустите руку вниз (~{round(angle)}°), затем новый отвод — "
                    "иначе повтор не засчитается."
                )
                correctness = "Опустите до исхода"

            elif neutral_low <= angle <= neutral_high:
                feedback = f"Середина отведения (~{round(angle)}°). Локоть чуть согнут."
                correctness = "Амплитуда хорошая"

            elif angle > 100:
                feedback = "Отвели слишком высоко — опустите на несколько градусов."
                correctness = "Слишком высоко"

        if self.reps >= target_reps:
            feedback = f"Цель достигнута: {self.reps} из {target_reps}."
            correctness = "Упражнение завершено"
            tips = ["Отлично.", "При боли уменьшите амплитуду в следующий раз."]
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
                    high_warn=100,
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
