"""Цветной скелет: рабочая сторона ярко, остальное приглушённо."""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

# BGR
_CLR_ACTIVE_JOINT = (255, 120, 0)  # оранжево-янтарный центр
_CLR_ACTIVE_BONE = (0, 255, 220)  # бирюзовые кости
_CLR_ACTIVE_GLOW = (40, 140, 255)
_CLR_DUAL_JOINT = (255, 200, 60)
_CLR_DUAL_BONE = (60, 255, 180)
_CLR_INACTIVE_JOINT = (110, 110, 110)
_CLR_INACTIVE_BONE = (70, 70, 70)
_CLR_LEG_JOINT = (0, 200, 255)
_CLR_LEG_BONE = (255, 180, 0)


def active_keypoint_names(
    model_side: str,
    *,
    use_legs: bool,
    dual_arms: bool,
    hip_shoulder_elbow_only: bool,
) -> set[str]:
    if dual_arms:
        parts = ("shoulder", "elbow", "wrist", "hip")
        return {f"{s}_{p}" for s in ("left", "right") for p in parts}
    if use_legs:
        return {f"{model_side}_hip", f"{model_side}_knee", f"{model_side}_ankle"}
    names = {
        f"{model_side}_shoulder",
        f"{model_side}_elbow",
        f"{model_side}_hip",
    }
    if not hip_shoulder_elbow_only:
        names.add(f"{model_side}_wrist")
    return names


def _pt(kpts: dict[str, Any], name: str, thr: float) -> tuple[int, int] | None:
    p = kpts.get(name)
    if not p or float(p.get("conf", 0)) < thr:
        return None
    return int(p["x"]), int(p["y"])


def _draw_bone(
    frame: np.ndarray,
    kpts: dict[str, Any],
    a: str,
    b: str,
    thr: float,
    color: tuple[int, int, int],
    thickness: int,
    glow: bool,
) -> None:
    p1 = _pt(kpts, a, thr)
    p2 = _pt(kpts, b, thr)
    if p1 is None or p2 is None:
        return
    if glow:
        cv2.line(frame, p1, p2, _CLR_ACTIVE_GLOW, thickness + 5, lineType=cv2.LINE_AA)
    cv2.line(frame, p1, p2, color, thickness, lineType=cv2.LINE_AA)


def _draw_joint(
    frame: np.ndarray,
    kpts: dict[str, Any],
    name: str,
    thr: float,
    color: tuple[int, int, int],
    radius: int,
    glow: bool,
) -> None:
    p = _pt(kpts, name, thr)
    if p is None:
        return
    if glow:
        cv2.circle(frame, p, radius + 4, _CLR_ACTIVE_GLOW, -1, lineType=cv2.LINE_AA)
    cv2.circle(frame, p, radius, color, -1, lineType=cv2.LINE_AA)
    cv2.circle(frame, p, max(2, radius // 3), (255, 255, 255), -1, lineType=cv2.LINE_AA)


def _arm_chains(side: str, *, include_wrist: bool) -> tuple[list[str], list[tuple[str, str]]]:
    joints = [f"{side}_shoulder", f"{side}_elbow", f"{side}_hip"]
    if include_wrist:
        joints.append(f"{side}_wrist")
    bones = [
        (f"{side}_hip", f"{side}_shoulder"),
        (f"{side}_shoulder", f"{side}_elbow"),
    ]
    if include_wrist:
        bones.append((f"{side}_elbow", f"{side}_wrist"))
    return joints, bones


def _draw_arm_side(
    frame: np.ndarray,
    kpts: dict[str, Any],
    side: str,
    thr: float,
    *,
    active: bool,
    include_wrist: bool,
) -> None:
    joints, bones = _arm_chains(side, include_wrist=include_wrist)
    if active:
        for a, b in bones:
            _draw_bone(frame, kpts, a, b, thr, _CLR_ACTIVE_BONE, 5, glow=True)
        for name in joints:
            _draw_joint(frame, kpts, name, thr, _CLR_ACTIVE_JOINT, 9, glow=True)
    else:
        for a, b in bones:
            _draw_bone(frame, kpts, a, b, thr, _CLR_INACTIVE_BONE, 2, glow=False)
        for name in joints:
            _draw_joint(frame, kpts, name, thr, _CLR_INACTIVE_JOINT, 5, glow=False)


def _leg_chain_visible(kpts: dict[str, Any], side: str, thr: float) -> bool:
    for part in ("hip", "knee", "ankle"):
        if _pt(kpts, f"{side}_{part}", thr) is None:
            return False
    return True


def resolve_leg_draw_side(
    kpts: dict[str, Any],
    assigned_side: str,
    thr: float,
) -> str:
    """Отрисовка: назначенная нога; если не видна — вторая (чтобы скелет не «ломался»)."""
    draw_thr = max(0.16, thr - 0.12)
    if _leg_chain_visible(kpts, assigned_side, draw_thr):
        return assigned_side
    other = "right" if assigned_side == "left" else "left"
    if _leg_chain_visible(kpts, other, draw_thr):
        return other
    return assigned_side


def _draw_leg_side(
    frame: np.ndarray,
    kpts: dict[str, Any],
    side: str,
    thr: float,
    *,
    active: bool,
    profile: bool = True,
) -> None:
    draw_thr = max(0.16, thr - 0.1) if active else thr
    joints = [f"{side}_hip", f"{side}_knee", f"{side}_ankle"]
    bones: list[tuple[str, str]] = [
        (f"{side}_hip", f"{side}_knee"),
        (f"{side}_knee", f"{side}_ankle"),
    ]
    if profile:
        joints = [f"{side}_shoulder", *joints]
        bones = [(f"{side}_shoulder", f"{side}_hip"), *bones]
    if active:
        for a, b in bones:
            _draw_bone(frame, kpts, a, b, draw_thr, _CLR_LEG_BONE, 6, glow=True)
        for name in joints:
            _draw_joint(frame, kpts, name, draw_thr, _CLR_LEG_JOINT, 10, glow=True)
        _draw_knee_angle_hint(frame, kpts, side, draw_thr)
    else:
        for a, b in bones:
            _draw_bone(frame, kpts, a, b, draw_thr, _CLR_INACTIVE_BONE, 2, glow=False)
        for name in joints:
            _draw_joint(frame, kpts, name, draw_thr, _CLR_INACTIVE_JOINT, 5, glow=False)


def _draw_knee_angle_hint(
    frame: np.ndarray,
    kpts: dict[str, Any],
    side: str,
    thr: float,
) -> None:
    """Дуга у колена (угол бедро–колено–голень), как в логике приседа."""
    hip = _pt(kpts, f"{side}_hip", thr)
    knee = _pt(kpts, f"{side}_knee", thr)
    ankle = _pt(kpts, f"{side}_ankle", thr)
    if hip is None or knee is None or ankle is None:
        return
    v1 = (hip[0] - knee[0], hip[1] - knee[1])
    v2 = (ankle[0] - knee[0], ankle[1] - knee[1])
    a1 = math.degrees(math.atan2(v1[1], v1[0]))
    a2 = math.degrees(math.atan2(v2[1], v2[0]))
    start = int(min(a1, a2))
    end = int(max(a1, a2))
    if end - start > 180:
        start, end = end, start + 360
    cv2.ellipse(
        frame,
        knee,
        (28, 28),
        0,
        start,
        end,
        (0, 255, 200),
        2,
        lineType=cv2.LINE_AA,
    )


def draw_pose_overlay(
    frame: np.ndarray,
    kpts: dict[str, Any],
    model_side: str,
    thr: float,
    *,
    use_legs: bool,
    dual_arms: bool,
    hip_shoulder_elbow_only: bool,
) -> None:
    """Сначала слабый контур всего тела, затем ярко — рабочая сторона."""
    if dual_arms and not use_legs:
        for side in ("left", "right"):
            _draw_arm_side(frame, kpts, side, thr, active=True, include_wrist=True)
        return

    if use_legs:
        active = resolve_leg_draw_side(kpts, model_side, thr)
        other = "right" if active == "left" else "left"
        _draw_leg_side(frame, kpts, other, thr, active=False, profile=True)
        _draw_leg_side(frame, kpts, active, thr, active=True, profile=True)
        return

    other = "right" if model_side == "left" else "left"
    include_wrist = not hip_shoulder_elbow_only
    _draw_arm_side(frame, kpts, other, thr, active=False, include_wrist=True)
    _draw_arm_side(frame, kpts, model_side, thr, active=True, include_wrist=include_wrist)
