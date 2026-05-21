from __future__ import annotations

import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

from app.exercise_kinds import (
    DUAL_ARM_EXERCISES,
    LEG_EXERCISES,
    uses_frontal_stance,
    uses_hip_shoulder_elbow_angle_only,
)
from app.exercises import get_exercise
from app.pose_overlay import active_keypoint_names, draw_pose_overlay
from app.pose_tracking import (
    KeypointSmoother,
    PersonBoxStabilizer,
    arm_keypoint_min_conf,
    enumerate_person_scores,
    pose_predict_kwargs,
    smooth_alpha,
    smooth_alpha_active,
    yolo_model_name,
)
from app.side_labels import side_instrumental_phrase, side_label_full
from app.squat_profile import profile_score_from_detection
from app.state import get_state, update_state

_model = None

_camera: cv2.VideoCapture | None = None
_camera_owner: int | None = None

_pose_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="yolo_pose")


@dataclass
class _UserStreamCtx:
    kp_smoother: KeypointSmoother | None = None
    person_stab: PersonBoxStabilizer | None = None
    current_exercise_name: str | None = None
    current_exercise: Any = None
    last_session_active: bool = False
    # (assignment_id, active_side) — при смене сбрасываем стабилизатор и сглаживание, чтобы модель заново выбрала фигуру под нужную руку
    focal_key: tuple[int | None, str | None] | None = None
    cached_kpts: dict[str, Any] | None = None
    pose_skip_counter: int = 0
    last_state_push_ts: float = 0.0
    last_stream_yield_ts: float = 0.0
    camera_read_failures: int = 0
    pose_lock: threading.Lock = field(default_factory=threading.Lock)
    pose_future: Future | None = None


_stream_ctx: dict[int, _UserStreamCtx] = {}
# Счётчик поколения потока: старый MJPEG не должен закрывать камеру нового подхода.
_stream_generation: dict[int, int] = {}


def bump_stream_generation(user_id: int) -> int:
    n = _stream_generation.get(user_id, 0) + 1
    _stream_generation[user_id] = n
    return n


def _reset_stream_ctx(ctx: _UserStreamCtx) -> None:
    """Сброс счётчика повторов и трекинга (старый MJPEG-поток не должен держать reps=8)."""
    ctx.last_session_active = False
    ctx.current_exercise = None
    ctx.current_exercise_name = None
    ctx.kp_smoother = None
    ctx.person_stab = None
    ctx.focal_key = None
    _reset_pose_cache(ctx)
    ctx.last_state_push_ts = 0.0
    ctx.last_stream_yield_ts = 0.0
    ctx.camera_read_failures = 0
    ctx.pose_future = None


def _stream_stale(user_id: int, generation: int) -> bool:
    return _stream_generation.get(user_id, 0) != generation


def _try_consume_pose_future(ctx: _UserStreamCtx) -> None:
    """Забрать готовый результат YOLO, не отменяя задачу в полёте."""
    fut = ctx.pose_future
    if fut is None:
        return
    if not fut.done():
        return
    try:
        fut.result(timeout=0)
    except Exception:
        pass
    ctx.pose_future = None


def _drain_pose_future(ctx: _UserStreamCtx, timeout: float = 0.4) -> None:
    """Дождаться YOLO (смена упражнения, остановка)."""
    fut = ctx.pose_future
    if fut is None:
        return
    try:
        fut.result(timeout=timeout)
    except Exception:
        pass
    ctx.pose_future = None


def _finish_pose_future(ctx: _UserStreamCtx) -> None:
    _try_consume_pose_future(ctx)


def _infer_pose_worker(
    user_id: int,
    generation: int,
    frame,
    predict_kw: dict[str, Any],
    prefer_pick: str | None,
    active_names: set[str] | None,
    *,
    pick_profile_squat: bool = False,
    prefer_legs: bool = False,
) -> None:
    if _stream_stale(user_id, generation):
        return
    ctx = _ctx(user_id)
    try:
        results = _get_model().predict(frame, **predict_kw)
        if _stream_stale(user_id, generation):
            return
        result = results[0] if results else None
        if result is None or result.keypoints is None:
            return
        with ctx.pose_lock:
            if _stream_stale(user_id, generation):
                return
            fresh = get_person_keypoints(
                result,
                ctx,
                prefer_pick,
                active_names=active_names,
                pick_profile_squat=pick_profile_squat,
                prefer_legs=prefer_legs,
            )
            if fresh:
                ctx.cached_kpts = fresh
    except Exception:
        pass


def prepare_training_camera(user_id: int) -> int:
    """
    Новый подход: увеличивает поколение потока и сбрасывает контекст на месте.
    Старый цикл generate_frames завершается, не закрывая камеру для нового подхода.
    """
    gen = bump_stream_generation(user_id)
    ctx = _ctx(user_id)
    _drain_pose_future(ctx, timeout=0.35)
    _reset_stream_ctx(ctx)
    with ctx.pose_lock:
        ctx.cached_kpts = None
    try:
        _get_model()
    except Exception:
        pass
    return gen


def stop_training_camera(user_id: int) -> None:
    """Остановить подход: убить старый MJPEG, дождаться YOLO, освободить камеру."""
    bump_stream_generation(user_id)
    if user_id in _stream_ctx:
        ctx = _stream_ctx[user_id]
        _drain_pose_future(ctx, timeout=0.5)
        _reset_stream_ctx(ctx)
        with ctx.pose_lock:
            ctx.cached_kpts = None
    release_camera_if_owner(user_id)


def release_camera_if_owner(user_id: int) -> None:
    """Освободить физическую камеру (без повторного bump поколения)."""
    global _camera, _camera_owner
    if _camera is not None and _camera_owner == user_id:
        try:
            _camera.release()
        except Exception:
            pass
        _camera = None
        _camera_owner = None
        if os.name == "nt":
            time.sleep(0.2)

_JPEG_PARAMS = [int(cv2.IMWRITE_JPEG_QUALITY), int(os.environ.get("VIDEO_JPEG_QUALITY", "82"))]


def _pose_infer_stride() -> int:
    v = int(os.environ.get("YOLO_STREAM_STRIDE", "2"))
    return max(1, min(v, 6))


def _stream_yield_interval_s() -> float:
    v = float(os.environ.get("VIDEO_STREAM_INTERVAL_MS", "66"))
    return max(0.04, min(v, 200.0)) / 1000.0


def _state_push_interval_s() -> float:
    v = float(os.environ.get("STATE_PUSH_INTERVAL_MS", "120"))
    return max(0.05, min(v, 500.0)) / 1000.0


def _reset_pose_cache(ctx: _UserStreamCtx) -> None:
    ctx.cached_kpts = None
    ctx.pose_skip_counter = 0


def _ctx(user_id: int) -> _UserStreamCtx:
    if user_id not in _stream_ctx:
        _stream_ctx[user_id] = _UserStreamCtx()
    return _stream_ctx[user_id]


def _get_model():
    global _model
    if _model is None:
        _model = YOLO(yolo_model_name())
    return _model


def _kp_threshold() -> float:
    return arm_keypoint_min_conf()


def _open_camera_capture() -> cv2.VideoCapture | None:
    """Windows: CAP_DSHOW стабильнее; иначе индекс 0 по умолчанию."""
    attempts: list[int | None] = []
    if os.name == "nt":
        attempts.append(cv2.CAP_DSHOW)
    attempts.append(None)
    for backend in attempts:
        cap = cv2.VideoCapture(0, backend) if backend is not None else cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            return cap
        cap.release()
    return None


def _ensure_camera_for(user_id: int) -> bool:
    """Одна физическая камера на процесс: открыть или подтвердить владение этим user_id."""
    global _camera, _camera_owner
    if _camera is not None and _camera_owner == user_id:
        if _camera.isOpened():
            return True
        try:
            _camera.release()
        except Exception:
            pass
        _camera = None
        _camera_owner = None
    if _camera is not None and _camera_owner != user_id:
        return False
    for attempt in range(4):
        cap = _open_camera_capture()
        if cap is not None:
            _camera = cap
            _camera_owner = user_id
            return True
        if os.name == "nt" and attempt < 3:
            time.sleep(0.15 * (attempt + 1))
    return False


def _mjpeg_chunk(frame) -> bytes | None:
    ret, buffer = cv2.imencode(".jpg", frame, _JPEG_PARAMS)
    if not ret:
        return None
    frame_bytes = buffer.tobytes()
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
    )


KEYPOINT_MAP = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
}


def stop_camera(user_id: int) -> None:
    """Освободить ресурсы стрима для пациента; камеру — только если он её держал."""
    release_camera_if_owner(user_id)


def get_person_keypoints(
    result,
    ctx: _UserStreamCtx,
    prefer_model_side: str | None = None,
    *,
    active_names: set[str] | None = None,
    pick_profile_squat: bool = False,
    prefer_legs: bool = False,
):
    if result.keypoints is None:
        return None

    xy = result.keypoints.xy
    conf = result.keypoints.conf

    if xy is None or len(xy) == 0:
        return None

    if ctx.person_stab is None:
        ctx.person_stab = PersonBoxStabilizer()
    if ctx.kp_smoother is None:
        ctx.kp_smoother = KeypointSmoother(smooth_alpha(), smooth_alpha_active())
    ctx.kp_smoother.set_active_names(active_names)

    scored, boxes = enumerate_person_scores(
        result, prefer_model_side, prefer_legs=prefer_legs
    )
    if pick_profile_squat and scored:
        xy_np = xy.cpu().numpy() if hasattr(xy, "cpu") else np.asarray(xy)
        conf_all = conf.cpu().numpy() if conf is not None and hasattr(conf, "cpu") else conf
        adjusted: list[tuple[int, float]] = []
        for i, s in scored:
            c_row = conf_all[i] if conf_all is not None else np.ones(17)
            bonus = profile_score_from_detection(np.asarray(c_row), xy_np[i])
            adjusted.append((i, s + bonus))
        adjusted.sort(key=lambda t: t[1], reverse=True)
        scored = adjusted
    person_i = ctx.person_stab.pick(scored, boxes)
    person_xy = xy[person_i].cpu().numpy()
    person_conf = conf[person_i].cpu().numpy() if conf is not None else None

    keypoints = {}
    for name, idx in KEYPOINT_MAP.items():
        x, y = person_xy[idx]
        score = person_conf[idx] if person_conf is not None else 1.0
        keypoints[name] = {
            "x": float(x),
            "y": float(y),
            "conf": float(score),
        }

    return ctx.kp_smoother.apply(keypoints)


def get_model_side(user_side: str) -> str:
    """Руки к камере: после зеркала кадра левая/правая в кадре меняются местами."""
    if user_side == "left":
        return "right"
    return "left"


def get_tracking_side(user_side: str, *, use_legs: bool) -> str:
    """Присед/нога в профиль: сторона по назначению, без зеркальной инверсии."""
    if user_side in ("left", "right"):
        return user_side if use_legs else get_model_side(user_side)
    return "left"


def extract_points(kpts, side):
    thr = _kp_threshold()
    required = [
        f"{side}_shoulder",
        f"{side}_elbow",
        f"{side}_wrist",
        f"{side}_hip",
    ]

    for name in required:
        if name not in kpts or kpts[name]["conf"] < thr:
            return None

    return {
        f"{side}_shoulder": (kpts[f"{side}_shoulder"]["x"], kpts[f"{side}_shoulder"]["y"]),
        f"{side}_elbow": (kpts[f"{side}_elbow"]["x"], kpts[f"{side}_elbow"]["y"]),
        f"{side}_wrist": (kpts[f"{side}_wrist"]["x"], kpts[f"{side}_wrist"]["y"]),
        f"{side}_hip": (kpts[f"{side}_hip"]["x"], kpts[f"{side}_hip"]["y"]),
    }


def extract_hip_shoulder_elbow_chain(kpts, side):
    """Только бедро–плечо–локоть: для отведения/подъёма в плоскости камеры без обязательного запястья."""
    base = _kp_threshold()
    thr = max(0.14, base - 0.12)
    required = [f"{side}_hip", f"{side}_shoulder", f"{side}_elbow"]
    for name in required:
        if name not in kpts or kpts[name]["conf"] < thr:
            return None
    return {
        f"{side}_hip": (kpts[f"{side}_hip"]["x"], kpts[f"{side}_hip"]["y"]),
        f"{side}_shoulder": (kpts[f"{side}_shoulder"]["x"], kpts[f"{side}_shoulder"]["y"]),
        f"{side}_elbow": (kpts[f"{side}_elbow"]["x"], kpts[f"{side}_elbow"]["y"]),
    }


def extract_leg_points(kpts, side):
    base = _kp_threshold()
    thr = max(0.14, base - 0.12)
    required = [f"{side}_hip", f"{side}_knee", f"{side}_ankle"]

    for name in required:
        if name not in kpts or kpts[name]["conf"] < thr:
            return None

    return {
        f"{side}_hip": (kpts[f"{side}_hip"]["x"], kpts[f"{side}_hip"]["y"]),
        f"{side}_knee": (kpts[f"{side}_knee"]["x"], kpts[f"{side}_knee"]["y"]),
        f"{side}_ankle": (kpts[f"{side}_ankle"]["x"], kpts[f"{side}_ankle"]["y"]),
    }


def _leg_visibility_score(kpts, side: str) -> float:
    total = 0.0
    for joint in ("hip", "knee", "ankle"):
        p = kpts.get(f"{side}_{joint}")
        if p:
            total += float(p.get("conf", 0))
    return total


def extract_leg_points_any_visible(kpts, prefer_side: str):
    """Присед: нога с лучшей видимостью (при равенстве — назначенная сторона)."""
    other = "right" if prefer_side == "left" else "left"
    candidates: list[tuple[float, str]] = []
    for side in (prefer_side, other):
        pts = extract_leg_points(kpts, side)
        if pts is not None:
            score = _leg_visibility_score(kpts, side)
            if side != prefer_side:
                score -= 0.05
            candidates.append((score, side))
    if not candidates:
        return None, prefer_side
    candidates.sort(key=lambda t: t[0], reverse=True)
    best_side = candidates[0][1]
    return extract_leg_points(kpts, best_side), best_side


def extract_dual_side_points(kpts):
    merged = {}
    for side in ("left", "right"):
        pts = extract_points(kpts, side)
        if pts is None:
            return None
        merged.update(pts)
    return merged


def extract_dual_arm_points(kpts):
    """Дыхание с двумя руками: плечо–локоть–кисть, без обязательного бедра (профиль)."""
    base = _kp_threshold()
    thr = max(0.18, base - 0.08)
    wrist_thr = max(0.16, base - 0.14)
    merged: dict[str, tuple[float, float]] = {}
    for side in ("left", "right"):
        names = (f"{side}_shoulder", f"{side}_elbow", f"{side}_wrist")
        thresholds = (thr, thr, wrist_thr)
        for name, t in zip(names, thresholds):
            p = kpts.get(name)
            if not p or float(p.get("conf", 0)) < t:
                return None
            merged[name] = (float(p["x"]), float(p["y"]))
    return merged


def _safe_update_state(user_id: int, generation: int, **kwargs: Any) -> None:
    if _stream_stale(user_id, generation):
        return
    update_state(user_id, **kwargs)


def generate_frames(user_id: int):
    ctx = _ctx(user_id)
    my_generation = _stream_generation.get(user_id, 0)
    base_predict_kw = pose_predict_kwargs(stream=True)
    stream_yield_iv = _stream_yield_interval_s()
    state_push_iv = _state_push_interval_s()

    while True:
        if _stream_stale(user_id, my_generation):
            break

        state = get_state(user_id)

        if not state["session_active"]:
            break

        if not _ensure_camera_for(user_id):
            _safe_update_state(
                user_id,
                my_generation,
                feedback="Камера занята другой сессией. Подождите или обновите страницу.",
                correctness="Камера недоступна",
                phase="waiting_start",
                tips=["На сервере одна камера — одновременно может тренироваться только один пациент."],
            )
            break

        if _stream_stale(user_id, my_generation):
            break

        selected_exercise = state["selected_exercise"]
        user_side = state["active_side"]
        use_legs = selected_exercise in LEG_EXERCISES
        track_side = get_tracking_side(user_side, use_legs=use_legs)
        model_side = track_side if use_legs else get_model_side(user_side)
        target_reps = state["target_reps"]
        dual_arms = selected_exercise in DUAL_ARM_EXERCISES
        hs_elbow_only = uses_hip_shoulder_elbow_angle_only(selected_exercise)
        active_names = active_keypoint_names(
            model_side,
            use_legs=use_legs,
            dual_arms=dual_arms,
            hip_shoulder_elbow_only=hs_elbow_only,
        )

        if not ctx.last_session_active:
            if _stream_stale(user_id, my_generation):
                break
            ctx.current_exercise_name = selected_exercise
            ctx.current_exercise = get_exercise(selected_exercise)
            ctx.current_exercise.reset()
            ctx.last_session_active = True
            ctx.kp_smoother = None
            ctx.person_stab = None
            _drain_pose_future(ctx, timeout=0.35)
            _reset_pose_cache(ctx)

        if ctx.current_exercise is None or ctx.current_exercise_name != selected_exercise:
            ctx.current_exercise_name = selected_exercise
            ctx.current_exercise = get_exercise(selected_exercise)
            ctx.current_exercise.reset()
            ctx.kp_smoother = None
            ctx.person_stab = None
            ctx.focal_key = None
            _drain_pose_future(ctx, timeout=0.2)
            _reset_pose_cache(ctx)

        aid_raw = state.get("assignment_id")
        try:
            aid_int = int(aid_raw) if aid_raw is not None else None
        except (TypeError, ValueError):
            aid_int = None
        side_k = user_side if isinstance(user_side, str) else None
        cur_focal: tuple[int | None, str | None] = (aid_int, side_k)
        if ctx.focal_key is not None and ctx.focal_key != cur_focal:
            ctx.kp_smoother = None
            ctx.person_stab = None
            if ctx.current_exercise is not None:
                ctx.current_exercise.reset()
            _drain_pose_future(ctx, timeout=0.15)
            _reset_pose_cache(ctx)
        ctx.focal_key = cur_focal

        assert _camera is not None
        success, frame = _camera.read()
        if not success:
            ctx.camera_read_failures += 1
            if ctx.camera_read_failures < 20:
                time.sleep(0.04)
                continue
            _safe_update_state(
                user_id,
                my_generation,
                feedback="Не удалось получить кадр с камеры. Закройте другие программы с веб-камерой и нажмите «Остановить», затем снова «Начать подход».",
                correctness="Камера недоступна",
                phase="waiting_start",
            )
            break
        ctx.camera_read_failures = 0

        frame = cv2.flip(frame, 1)

        infer_stride = _pose_infer_stride()
        ctx.pose_skip_counter += 1
        rep_sensitive = selected_exercise in (
            "partial_squat",
            "forward_raise",
            "arm_raise",
        )
        pose_every_frame = hs_elbow_only or rep_sensitive
        run_pose = pose_every_frame or ctx.pose_skip_counter >= infer_stride
        prefer_pick: str | None = None if (dual_arms and not use_legs) else model_side
        squat_pick = selected_exercise == "partial_squat"

        _try_consume_pose_future(ctx)
        if run_pose and ctx.pose_future is None:
            ctx.pose_skip_counter = 0
            ctx.pose_future = _pose_executor.submit(
                _infer_pose_worker,
                user_id,
                my_generation,
                frame.copy(),
                base_predict_kw,
                prefer_pick,
                active_names,
                pick_profile_squat=squat_pick,
                prefer_legs=use_legs,
            )

        with ctx.pose_lock:
            kpts = ctx.cached_kpts
        thr = _kp_threshold()

        if kpts:
            draw_pose_overlay(
                frame,
                kpts,
                model_side,
                thr,
                use_legs=use_legs,
                dual_arms=dual_arms,
                hip_shoulder_elbow_only=hs_elbow_only,
            )
            leg_detect_side = model_side
            if use_legs:
                if selected_exercise == "partial_squat":
                    points, leg_detect_side = extract_leg_points_any_visible(
                        kpts, model_side
                    )
                else:
                    points = extract_leg_points(kpts, model_side)
            elif dual_arms:
                points = extract_dual_arm_points(kpts) or extract_dual_side_points(kpts)
            elif hs_elbow_only:
                points = extract_hip_shoulder_elbow_chain(kpts, model_side)
            else:
                points = extract_points(kpts, model_side)

            if points and ctx.current_exercise is not None:
                try:
                    metrics = ctx.current_exercise.detect(
                        points,
                        side=leg_detect_side if use_legs else model_side,
                        target_reps=target_reps,
                    )
                except Exception:
                    metrics = None
                if metrics:
                    tips = list(metrics.get("tips") or [])
                    update_kw: dict[str, Any] = {
                        "feedback": metrics["feedback"],
                        "angle": metrics["angle"],
                        "phase": metrics["phase"],
                        "reps": metrics["reps"],
                        "correctness": metrics["correctness"],
                        "tips": tips,
                    }
                    now = time.monotonic()
                    if now - ctx.last_state_push_ts >= state_push_iv:
                        _safe_update_state(user_id, my_generation, **update_kw)
                        ctx.last_state_push_ts = now

                    if int(metrics.get("reps") or 0) >= int(target_reps):
                        done_reps = int(metrics.get("reps") or target_reps)
                        _safe_update_state(
                            user_id,
                            my_generation,
                            reps=done_reps,
                            session_active=False,
                            completed=True,
                            feedback=f"Упражнение завершено. Выполнено {done_reps} из {target_reps}.",
                            correctness="Цель достигнута",
                            phase="finished",
                            tips=[
                                "Упражнение завершено.",
                                "Можно немного отдохнуть.",
                                "Чтобы начать снова, выберите настройки и нажмите «Начать».",
                            ],
                        )
            else:
                side_tip = side_instrumental_phrase(
                    user_side if user_side in ("left", "right") else "left",
                    selected_exercise,
                )
                if use_legs:
                    if selected_exercise == "partial_squat":
                        tips = [
                            f"Стоя боком, сейчас {side_tip} — бедро, колено и голень в кадре.",
                            "Встаньте боком к камере на 1,5–2,5 м; рабочая нога ближе к объективу.",
                        ]
                    else:
                        tips = [
                            f"Сейчас работайте {side_tip} — бедро, колено и голень должны быть в кадре.",
                            "Встаньте боком к камере на 1,5–2,5 м: бедро, колено и голень рабочей ноги в кадре.",
                        ]
                    fb = (
                        f"Бедро, колено и голень ({side_tip}) определяются неуверенно. "
                        "Отойдите чуть назад или поправьте свет."
                    )
                elif dual_arms:
                    tips = [
                        "Встаньте боком или четвертью поворотом: обе руки от плеча до кисти в кадре.",
                        "Силуэт корпуса сбоку; руки двигаются синхронно вверх и вниз.",
                        "При слабом свете — яркий свет сбоку от себя, не из-за спины.",
                    ]
                    fb = (
                        "Обе руки должны быть в кадре целиком: плечо, локоть и запястье слева и справа."
                    )
                elif uses_frontal_stance(selected_exercise):
                    tips = [
                        f"Встаньте прямо лицом к камере — работайте {side_tip}.",
                        "Рука вдоль бедра → подъём вперёд-вверх → опускание вниз; не боком к камере.",
                        "В кадре: плечо, локоть и кисть; корпус прямой. Отойдите на 1,5–2,5 м.",
                    ]
                    side_word = f"{'Левая' if user_side == 'left' else 'Правая'} "
                    fb = (
                        f"{side_word}рука определяется неуверенно. "
                        "Встаньте прямо к камере, отойдите чуть назад или поправьте свет."
                    )
                else:
                    tips = [
                        f"Встаньте боком к камере — работайте {side_tip}, эта сторона ближе к объективу.",
                        "В кадре: плечо, локоть и кисть рабочей руки, силуэт корпуса сбоку.",
                        "Отойдите на 1,5–2,5 м; не начинайте, пока точки не определяются уверенно.",
                    ]
                    side_word = f"{'Левая' if user_side == 'left' else 'Правая'} "
                    fb = (
                        f"{side_word}рука определяется неуверенно. "
                        "Отойдите чуть назад или поправьте свет."
                    )
                now = time.monotonic()
                if now - ctx.last_state_push_ts >= state_push_iv:
                    _safe_update_state(
                        user_id,
                        my_generation,
                        feedback=fb,
                        correctness="Точки плохо видны — поправьте кадр",
                        phase="waiting_start",
                        tips=tips,
                    )
                    ctx.last_state_push_ts = now
        else:
            if uses_frontal_stance(selected_exercise):
                no_pose_tips = [
                    "Встаньте прямо лицом к камере — не боком и не спиной.",
                    "Рабочая рука в кадре: опустите её вдоль бедра, затем подъём вперёд-вверх.",
                    "Освещение спереди: лицо, плечо, локоть и кисть должны быть видны.",
                ]
            else:
                no_pose_tips = [
                    "Встаньте боком к камере, рабочая сторона ближе к объективу.",
                    "Проверьте освещение сбоку от себя.",
                    "После входа в кадр примите исходное положение.",
                ]
            if not dual_arms and not use_legs:
                side_tip = side_instrumental_phrase(
                    user_side if user_side in ("left", "right") else "left",
                    selected_exercise,
                )
                no_pose_tips.insert(
                    0,
                    f"Назначена {side_label_full(user_side, selected_exercise).lower()} — работайте {side_tip}.",
                )
            elif use_legs:
                side_tip = side_instrumental_phrase(
                    user_side if user_side in ("left", "right") else "left",
                    selected_exercise,
                )
                no_pose_tips.insert(0, f"Работайте {side_tip}.")
            now = time.monotonic()
            if now - ctx.last_state_push_ts >= state_push_iv:
                _safe_update_state(
                    user_id,
                    my_generation,
                    feedback="Человек не найден. Зайдите в кадр перед камерой.",
                    correctness="Нет позы",
                    phase="waiting_start",
                    tips=no_pose_tips,
                )
                ctx.last_state_push_ts = now

        if _stream_stale(user_id, my_generation):
            break

        now_out = time.monotonic()
        if now_out - ctx.last_stream_yield_ts >= stream_yield_iv:
            out_chunk = _mjpeg_chunk(frame)
            if out_chunk:
                yield out_chunk
                ctx.last_stream_yield_ts = now_out

    _drain_pose_future(ctx, timeout=0.15)
    ctx.last_session_active = False
    if not _stream_stale(user_id, my_generation):
        release_camera_if_owner(user_id)
