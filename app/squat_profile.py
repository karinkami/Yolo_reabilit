"""Проверка: присед выполняется стоя боком (профиль), а не лицом/спиной к камере."""

from __future__ import annotations

from typing import Any

import numpy as np

# COCO: 5/6 плечи, 11/12 бедра
_SH_L, _SH_R = 5, 6
_HIP_L, _HIP_R = 11, 12


def _conf_xy(conf: np.ndarray, xy: np.ndarray, idx: int) -> tuple[float, float, float] | None:
    if conf.size <= idx:
        return None
    c = float(conf[idx])
    if c < 0.12:
        return None
    return c, float(xy[idx][0]), float(xy[idx][1])


def profile_score_from_detection(conf: np.ndarray, xy: np.ndarray) -> float:
    """Бонус к выбору человека: выше, если в кадре профиль, а не фас."""
    bonus = 0.0
    ls = _conf_xy(conf, xy, _SH_L)
    rs = _conf_xy(conf, xy, _SH_R)
    lh = _conf_xy(conf, xy, _HIP_L)
    rh = _conf_xy(conf, xy, _HIP_R)
    if ls and rs and lh and rh:
        sh_span = abs(ls[1] - rs[1])
        hip_span = abs(lh[1] - rh[1]) + 1e-6
        ratio = sh_span / hip_span
        if ratio < 0.42:
            bonus += 0.22
        elif ratio > 0.62:
            bonus -= 0.18
        if abs(ls[0] - rs[0]) > 0.18:
            bonus += 0.12
    leg_idx = (_HIP_L, 13, 15)
    leg_vis = sum(1 for i in leg_idx if conf.size > i and float(conf[i]) >= 0.28)
    if leg_vis >= 2:
        bonus += 0.08
    return bonus


def squat_profile_ok(
    kpts: dict[str, Any],
    work_side: str,
    thr: float,
) -> tuple[bool, str]:
    """
    Мягкая проверка: рабочая нога в кадре; явный фас — подсказка повернуться.
    Не проверяем «вертикаль ноги» — при сгибании колена она ломает подсчёт.
    """
    draw_thr = max(0.14, thr - 0.14)

    def pt(name: str) -> tuple[float, float, float] | None:
        p = kpts.get(name)
        if not p:
            return None
        c = float(p.get("conf", 0))
        if c < draw_thr:
            return None
        return c, float(p["x"]), float(p["y"])

    wh = pt(f"{work_side}_hip")
    wk = pt(f"{work_side}_knee")
    wa = pt(f"{work_side}_ankle")

    if not (wh and wk and wa):
        return (
            False,
            "Встаньте боком к камере: в кадре должны быть бедро, колено и щиколотка рабочей ноги.",
        )

    ls = pt("left_shoulder")
    rs = pt("right_shoulder")
    lh = pt("left_hip")
    rh = pt("right_hip")
    if ls and rs and lh and rh:
        sh_span = abs(ls[1] - rs[1])
        hip_span = abs(lh[1] - rh[1]) + 1e-6
        if sh_span / hip_span > 0.72:
            return (
                False,
                "Повернитесь боком к камере — не лицом и не спиной к объективу.",
            )

    return True, ""
