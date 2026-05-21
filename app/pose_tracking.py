"""Выбор человека в кадре, стабильность «своего» человека и сглаживание ключевых точек."""

from __future__ import annotations

import os
from typing import Any

import numpy as np


# COCO (Ultralytics pose): плечо–локоть–кисть + бедро той же стороны — для приоритета рабочей руки
_MODEL_SIDE_TO_INDICES: dict[str, tuple[int, ...]] = {
    "left": (5, 7, 9, 11),
    "right": (6, 8, 10, 12),
}

# Профиль / присед: бедро–колено–щиколотка и плечо той же стороны
_LEG_SIDE_TO_INDICES: dict[str, tuple[int, ...]] = {
    "left": (5, 11, 13, 15),
    "right": (6, 12, 14, 16),
}

# Все шесть точек рук — когда сторона не важна (две руки / ноги)
_ARM_CONF_INDICES = (5, 6, 7, 8, 9, 10)


def _to_numpy(x) -> np.ndarray:
    if x is None:
        return np.array([])
    return x.cpu().numpy() if hasattr(x, "cpu") else np.asarray(x)


def _iou_xyxy(a: np.ndarray, b: np.ndarray) -> float:
    ax1, ay1, ax2, ay2 = a.astype(np.float64)
    bx1, by1, bx2, by2 = b.astype(np.float64)
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    aa = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    ba = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = aa + ba - inter + 1e-9
    return float(inter / union)


def _person_score_for_index(
    i: int,
    conf: np.ndarray,
    boxes: np.ndarray | None,
    h: int,
    w: int,
    prefer_model_side: str | None,
    *,
    prefer_legs: bool = False,
) -> float:
    if conf.size < 17:
        conf = np.pad(conf, (0, max(0, 17 - conf.size)), constant_values=0.5)

    fc = np.array([w * 0.5, h * 0.5], dtype=np.float64)
    diag = float(np.hypot(w, h)) + 1e-6

    side_map = _LEG_SIDE_TO_INDICES if prefer_legs else _MODEL_SIDE_TO_INDICES
    if prefer_model_side in side_map:
        pref_idx = list(side_map[prefer_model_side])
        other_idx = [j for j in _ARM_CONF_INDICES if j not in pref_idx]
        pref_mean = float(np.mean(conf[pref_idx]))
        other_mean = float(np.mean(conf[other_idx])) if other_idx else pref_mean
        arm_blend = 0.78 * pref_mean + 0.22 * other_mean
    else:
        arm_blend = float(np.mean(conf[list(_ARM_CONF_INDICES)]))

    if boxes is not None and len(boxes) > i:
        x1, y1, x2, y2 = boxes[i].astype(np.float64)
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        dist = float(np.hypot(cx - fc[0], cy - fc[1]))
        center_score = max(0.0, 1.0 - dist / (0.42 * diag))
        area = max(float((x2 - x1) * (y2 - y1)), 1.0)
        area_norm = float(np.sqrt(area / (w * h + 1e-6)))
    else:
        center_score = 0.35
        area_norm = 0.22

    return 0.58 * arm_blend + 0.26 * center_score + 0.16 * min(area_norm, 0.85)


def enumerate_person_scores(
    result,
    prefer_model_side: str | None = None,
    *,
    prefer_legs: bool = False,
) -> tuple[list[tuple[int, float]], np.ndarray | None]:
    """Список (индекс детекции, оценка) по убыванию оценки; боксы xyxy или None."""
    kp = result.keypoints
    if kp is None or kp.xy is None:
        return [], None

    n = int(kp.xy.shape[0])
    orig = getattr(result, "orig_shape", None) or (720, 1280)
    h, w = int(orig[0]), int(orig[1])

    boxes = None
    if result.boxes is not None and result.boxes.xyxy is not None:
        b = _to_numpy(result.boxes.xyxy)
        if b.size and len(b) >= n:
            boxes = np.asarray(b[:n], dtype=np.float64)

    conf_all = kp.conf
    scored: list[tuple[int, float]] = []
    for i in range(n):
        conf = _to_numpy(conf_all[i]) if conf_all is not None else np.ones(17, dtype=np.float64)
        s = _person_score_for_index(
            i, conf, boxes, h, w, prefer_model_side, prefer_legs=prefer_legs
        )
        scored.append((i, s))

    scored.sort(key=lambda t: t[1], reverse=True)
    return scored, boxes


class PersonBoxStabilizer:
    """Не прыгать на другого человека: держим того же по IoU бокса, пока он в кадре."""

    def __init__(
        self,
        iou_keep: float | None = None,
        score_advantage_to_drop: float | None = None,
    ):
        self.iou_keep = float(iou_keep if iou_keep is not None else os.environ.get("POSE_PERSON_IOU_KEEP", "0.30"))
        self.iou_keep = max(0.15, min(self.iou_keep, 0.55))
        self.score_advantage = float(
            score_advantage_to_drop
            if score_advantage_to_drop is not None
            else os.environ.get("POSE_PERSON_SCORE_SWITCH", "0.11")
        )
        self.score_advantage = max(0.04, min(self.score_advantage, 0.35))
        self._prev_box: np.ndarray | None = None

    def reset(self) -> None:
        self._prev_box = None

    def pick(
        self,
        scored: list[tuple[int, float]],
        boxes: np.ndarray | None,
    ) -> int:
        if not scored:
            return 0
        if boxes is None or len(boxes) == 0:
            self._prev_box = None
            return scored[0][0]

        best_idx, best_score = scored[0]

        if self._prev_box is None:
            self._prev_box = boxes[best_idx].astype(np.float64).copy()
            return best_idx

        # Индекс -> оценка
        score_by_idx = {idx: sc for idx, sc in scored}

        n_det = len(scored)
        matches = [
            i
            for i in range(min(len(boxes), n_det))
            if _iou_xyxy(boxes[i], self._prev_box) >= self.iou_keep
        ]
        if matches:
            bi = max(matches, key=lambda i: score_by_idx.get(i, -1.0))
            bi_score = score_by_idx.get(bi, -1.0)
            if best_idx != bi and best_score > bi_score + self.score_advantage:
                chosen = best_idx
            else:
                chosen = bi
        else:
            chosen = best_idx

        self._prev_box = boxes[chosen].astype(np.float64).copy()
        return chosen


def pick_best_person_index(result, prefer_model_side: str | None = None) -> int:
    """Однокадровый выбор (без стабилизатора бокса) — для тестов и простых случаев."""
    scored, _ = enumerate_person_scores(result, prefer_model_side)
    if not scored:
        return 0
    return scored[0][0]


class KeypointSmoother:
    """EMA по x/y; на рабочих суставах — выше alpha (меньше задержка при движении)."""

    def __init__(self, alpha: float = 0.42, active_alpha: float | None = None):
        self.alpha = max(0.05, min(0.95, float(alpha)))
        self.active_alpha = float(active_alpha if active_alpha is not None else smooth_alpha_active())
        self.active_alpha = max(self.alpha, min(0.97, self.active_alpha))
        self._prev: dict[str, tuple[float, float]] = {}
        self._active: set[str] = set()

    def reset(self) -> None:
        self._prev.clear()

    def set_active_names(self, names: set[str] | None) -> None:
        self._active = set(names) if names else set()

    def apply(self, keypoints: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, val in keypoints.items():
            x = float(val["x"])
            y = float(val["y"])
            c = float(val.get("conf", 1.0))
            base = self.active_alpha if name in self._active else self.alpha
            if name in self._prev:
                px, py = self._prev[name]
                if c >= 0.5:
                    eff = base
                elif c >= 0.35:
                    eff = min(base, 0.55)
                else:
                    eff = min(base, 0.28)
                x = eff * x + (1.0 - eff) * px
                y = eff * y + (1.0 - eff) * py
            self._prev[name] = (x, y)
            out[name] = {"x": x, "y": y, "conf": c}
        return out


def pose_predict_kwargs(*, stream: bool = False) -> dict[str, Any]:
    """Параметры predict из окружения (можно переопределить без правки кода)."""
    if stream:
        default_imgsz = os.environ.get("YOLO_STREAM_IMGSZ", os.environ.get("YOLO_IMGSZ", "640"))
    else:
        default_imgsz = os.environ.get("YOLO_IMGSZ", "768")
    imgsz = int(default_imgsz)
    imgsz = max(320, min(imgsz, 1280))
    conf = float(os.environ.get("YOLO_PERSON_CONF", "0.28"))
    conf = max(0.1, min(conf, 0.9))
    iou = float(os.environ.get("YOLO_IOU", "0.5"))
    iou = max(0.2, min(iou, 0.95))
    max_det = int(os.environ.get("YOLO_MAX_DET", "6"))
    max_det = max(1, min(max_det, 20))
    return {
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "max_det": max_det,
        "verbose": False,
    }


def arm_keypoint_min_conf() -> float:
    v = float(os.environ.get("POSE_ARM_MIN_CONF", "0.30"))
    return max(0.15, min(v, 0.85))


def smooth_alpha() -> float:
    """Фоновые точки: умеренное сглаживание (стабильность)."""
    v = float(os.environ.get("POSE_SMOOTH_ALPHA", "0.52"))
    return max(0.08, min(v, 0.9))


def smooth_alpha_active() -> float:
    """Рабочая цепочка: ближе к сырому кадру — без заметной задержки."""
    v = float(os.environ.get("POSE_SMOOTH_ALPHA_ACTIVE", "0.82"))
    return max(0.35, min(v, 0.97))


def yolo_model_name() -> str:
    return (os.environ.get("YOLO_POSE_MODEL") or "yolo11n-pose.pt").strip() or "yolo11n-pose.pt"
