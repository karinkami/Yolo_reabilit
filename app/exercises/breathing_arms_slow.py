"""Тот же цикл, что «дыхание с руками», но медленнее — акцент на расслабление и ритм дыхания."""

from app.exercises.breathing_arms import BreathingArmsExercise


class BreathingArmsSlowExercise(BreathingArmsExercise):
    def __init__(self):
        super().__init__()
        self.name = "breathing_arms_slow"
        self.min_rep_interval = 3.2
