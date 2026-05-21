import math
from typing import Any, Tuple


def _xy(p: Any) -> Tuple[float, float]:
    if isinstance(p, (tuple, list)) and len(p) >= 2:
        return float(p[0]), float(p[1])
    if isinstance(p, dict) and "x" in p and "y" in p:
        return float(p["x"]), float(p["y"])
    return 0.0, 0.0


def angle_three_points(a, b, c) -> float:
    """Угол ABC в градусах. Точки — (x, y) или dict с ключами x, y."""
    ax, ay = _xy(a)
    bx, by = _xy(b)
    cx, cy = _xy(c)
    ba = (ax - bx, ay - by)
    bc = (cx - bx, cy - by)
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)
    if mag_ba == 0 or mag_bc == 0:
        return 0.0
    cos_angle = dot / (mag_ba * mag_bc)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))
