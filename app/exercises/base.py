import time


class BaseExercise:
    def __init__(self, name):
        self.name = name
        self.phase = "waiting_start"
        self.reps = 0
        self.ready = False
        self.last_rep_time = 0.0
        self.min_rep_interval = 1.15
        self._prev_angle = None
        self._prev_angle_t = None

    def reset(self):
        self.phase = "waiting_start"
        self.reps = 0
        self.ready = False
        self.last_rep_time = 0.0
        self._prev_angle = None
        self._prev_angle_t = None

    def angle_velocity_deg_s(self, angle: float) -> float:
        """Скорость изменения угла в градусах/с (для подсказок «медленнее»)."""
        now = time.time()
        if self._prev_angle is None or self._prev_angle_t is None:
            self._prev_angle = angle
            self._prev_angle_t = now
            return 0.0
        dt = now - self._prev_angle_t
        if dt <= 0.0:
            self._prev_angle = angle
            self._prev_angle_t = now
            return 0.0
        rate = (angle - self._prev_angle) / dt
        self._prev_angle = angle
        self._prev_angle_t = now
        return rate

    def can_count_rep(self):
        now = time.time()
        if now - self.last_rep_time >= self.min_rep_interval:
            self.last_rep_time = now
            return True
        return False

    def detect(self, keypoints, side="left", target_reps=10):
        raise NotImplementedError