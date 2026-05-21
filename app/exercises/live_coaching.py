"""Короткие подсказки по текущему углу, фазе и скорости движения (не общие лозунги)."""

from __future__ import annotations


def merge_tips(*groups: list[str], max_items: int = 4) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for g in groups:
        for s in g:
            t = (s or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
            if len(out) >= max_items:
                return out
    return out


def speed_tip_deg_s(rate: float, threshold: float = 95.0) -> list[str]:
    if abs(rate) >= threshold:
        return ["Сейчас движение слишком резкое — замедлите на треть–половину."]
    return []


def vertical_arm_sagittal(
    angle: float,
    phase: str,
    ready: bool,
    rate: float,
    *,
    start_thr: float,
    top_thr: float,
    neutral_low: float,
    neutral_high: float,
) -> list[str]:
    """Угол плечо–локоть–кисть: больше угол ≈ рука ниже (разгиб), меньше ≈ подъём вверх."""
    tips = list(speed_tip_deg_s(rate, 105.0))
    if not ready:
        if angle < start_thr - 15:
            tips.append("Выпрямите руку сильнее вниз вдоль тела — сейчас она недостаточно опущена.")
        elif angle < start_thr - 4:
            tips.append("Чуть сильнее разогните локоть книзу — почти исходное положение.")
        else:
            tips.append("Зафиксируйте низ на секунду, затем начинайте подъём.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle >= start_thr - 2:
        tips.append("Из низа ведите кисть плавно вверх, плечо не подтягивайте к уху.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle <= top_thr:
        return merge_tips(tips, max_items=4)

    if phase == "down" and top_thr < angle < start_thr:
        span = max(start_thr - top_thr, 1.0)
        progress = (angle - top_thr) / span
        if progress > 0.62:
            tips.append("Продолжайте подъём: кисть и предплечье ведите выше.")
        elif progress > 0.28:
            tips.append("Середина подъёма — держите ровный темп, без рывка.")
        else:
            tips.append("Дойдите до верхней точки комфортно — ещё немного вверх.")
        return merge_tips(tips, max_items=4)

    if phase == "up":
        if angle <= top_thr + 12:
            tips.append("С верхней точки начинайте плавное опускание, не «бросайте» руку.")
        elif angle < (start_thr + top_thr) / 2:
            tips.append("Опускайте руку ниже к исходной линии — сохраняйте контроль.")
        elif angle < start_thr - 6:
            tips.append("Почти внизу — слегка доложите до полного исхода перед следующим подъёмом.")
        else:
            tips.append("Исход зафиксирован — можно следующий медленный подъём.")
        return merge_tips(tips, max_items=4)

    if neutral_low <= angle <= neutral_high:
        if rate < -25:
            tips.append("Идёте на подъём — не ускоряйте в середине амплитуды.")
        elif rate > 35:
            tips.append("Идёте вниз — чуть мягче, без падения руки.")
        else:
            tips.append("Держите плавность в середине дуги — дышите ровно.")
        return merge_tips(tips, max_items=4)

    if angle < 70:
        tips.append("Слишком «короткий» резкий жест — разгибайте и сгибайте мягче по всей дуге.")
    return merge_tips(tips, max_items=4)


def abduction_side(
    angle: float,
    phase: str,
    ready: bool,
    rate: float,
    *,
    start_thr: float,
    top_thr: float,
    neutral_low: float,
    neutral_high: float,
    high_warn: float | None = None,
) -> list[str]:
    """Угол бедро–плечо–локоть при отведении: малый угол — рука внизу, больший — отведена."""
    tips = list(speed_tip_deg_s(rate, 85.0))
    if not ready:
        if angle > start_thr + 18:
            tips.append("Опустите и прижмите рабочую руку ближе к бедру — сейчас она слишком отведена для старта.")
        elif angle > start_thr + 4:
            tips.append("Чуть ниже к корпусу — почти исходное положение.")
        else:
            tips.append("Зафиксируйте низ, затем отводите руку в сторону по дуге.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle <= start_thr + 2:
        tips.append("Из нижней точки ведите локоть в сторону, корпус не заваливайте.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle >= top_thr:
        return merge_tips(tips, max_items=4)

    if phase == "down" and start_thr < angle < top_thr:
        span = max(top_thr - start_thr, 1.0)
        progress = (angle - start_thr) / span
        if progress < 0.35:
            tips.append("Продолжайте отведение в сторону — амплитуда пока маловата.")
        elif progress < 0.72:
            tips.append("Середина дуги — не поднимайте плечо к уху, локоть чуть вперёд.")
        else:
            tips.append("Почти верх отведения — доведите плавно, без рывка.")
        return merge_tips(tips, max_items=4)

    if phase == "up":
        if angle >= top_thr - 8:
            tips.append("С верхней точки ведите руку вниз так же контролируемо, как вверх.")
        elif angle > (start_thr + top_thr) / 2:
            tips.append("Опускайте ниже к бедру — не останавливайтесь «в воздухе».")
        elif angle > start_thr + 6:
            tips.append("Почти исход — слегка доложите до полного опускания вдоль тела.")
        else:
            tips.append("Исход внизу — можно следующий повтор.")
        return merge_tips(tips, max_items=4)

    if neutral_low <= angle <= neutral_high:
        if rate > 22:
            tips.append("Отводите дальше в сторону плавно — не рывком.")
        elif rate < -30:
            tips.append("Возврат вниз — мягче, без «падения» руки.")
        else:
            tips.append("В этой зоне держите ровный темп и ровный корпус.")
        return merge_tips(tips, max_items=4)

    if high_warn is not None and angle > high_warn:
        tips.append("Слишком высоко для этого упражнения — опустите на пару градусов в комфорт.")
    return merge_tips(tips, max_items=4)


def forward_raise(
    angle: float,
    phase: str,
    ready: bool,
    rate: float,
    *,
    start_thr: float,
    top_thr: float,
    neutral_low: float,
    neutral_high: float,
) -> list[str]:
    """Подъём вперёд: малый угол — внизу, больший — впереди выше."""
    tips = list(speed_tip_deg_s(rate, 70.0))
    if not ready:
        if angle > start_thr + 12:
            tips.append("Опустите руку ближе к корпусу — сейчас она слишком поднята для исхода.")
        elif angle > start_thr + 2:
            tips.append("Чуть ниже вдоль бедра — почти можно начинать подъём вперёд.")
        else:
            tips.append("Ведите ладонь прямо вперёд, локоть слегка согнут.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle <= start_thr + 2:
        tips.append("Из низа поднимайте руку перед собой, не заваливаясь назад.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle >= top_thr:
        return merge_tips(tips, max_items=4)

    if phase == "down" and start_thr < angle < top_thr:
        span = max(top_thr - start_thr, 1.0)
        p = (angle - start_thr) / span
        if p < 0.38:
            tips.append("Продолжайте подъём вперёд — предплечье чуть выше.")
        elif p < 0.78:
            tips.append("Середина — корпус прямой, не «выворачивайте» плечи.")
        else:
            tips.append("Почти уровень задания — доведите без рывка.")
        return merge_tips(tips, max_items=4)

    if phase == "up":
        if angle >= top_thr - 5:
            tips.append("Опускайте руку вперёд-вниз плавно, как подъёмали.")
        elif angle > start_thr + 10:
            tips.append("Возвращайте ниже к бедру — контролируйте каждые несколько градусов.")
        else:
            tips.append("Почти исход — зафиксируйте перед следующим повтором.")
        return merge_tips(tips, max_items=4)

    if neutral_low <= angle <= neutral_high:
        tips.append("Середина амплитуды — свяжите движение с ровным дыханием.")
    return merge_tips(tips, max_items=4)


def elbow_extension_moment(angle: float, phase: str, ready: bool, rate: float, *, bent_top: float, straight_min: float) -> list[str]:
    tips = list(speed_tip_deg_s(rate, 90.0))
    if not ready:
        if angle > bent_top + 12:
            tips.append("Сильнее согните локоть примерно до прямого угла визуально — сейчас разгиб слишком большой для старта.")
        elif angle > bent_top + 3:
            tips.append("Ещё чуть согните локоть — почти готовы к разгибанию.")
        return merge_tips(tips, max_items=4)

    if phase == "bent":
        tips.append("Из сгиба разгибайте локоть вперёд до почти прямого, без щелчка в конце.")
        return merge_tips(tips, max_items=4)

    if phase == "extended":
        tips.append("Теперь согните локоть обратно — полный цикл важнее скорости.")
        return merge_tips(tips, max_items=4)

    if bent_top < angle < straight_min:
        if rate > 40:
            tips.append("Доведите разгиб почти до прямого локтя — сейчас остановились «на середине».")
        elif rate < -35:
            tips.append("Не сгибайте обратно, пока не довели разгиб до конца контролируемо.")
        else:
            tips.append("Между сгибом и разгибом — двигайтесь без рывка через эту зону.")
    return merge_tips(tips, max_items=4)


def breathing_dual_moment(
    angle_avg: float,
    angle_left: float,
    angle_right: float,
    phase: str,
    ready: bool,
    rate: float,
    *,
    start_thr: float,
    top_thr: float,
    neutral_low: float,
    neutral_high: float,
    asym_soft: float,
) -> list[str]:
    tips = list(speed_tip_deg_s(rate, 55.0))
    diff = angle_left - angle_right
    if ready and abs(diff) > asym_soft / 2:
        if diff < -6:
            tips.append("Правая сейчас чуть выше левой — слегка опустите правую или поднимите левую до одной линии.")
        elif diff > 6:
            tips.append("Левая сейчас чуть выше правой — слегка опустите левую или поднимите правую до одной линии.")
    if not ready:
        if angle_avg < start_thr - 10:
            tips.append("Опустите обе руки ниже по корпусу — исход «внизу» для этого цикла.")
        elif angle_avg < start_thr - 2:
            tips.append("Чуть ниже обеими — почти можно синхронно начинать вдох вверх.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle_avg >= start_thr - 2:
        tips.append("Выдох: опускайте обе руки одновременно, не наклоняйтесь вперёд сильно.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and top_thr < angle_avg < start_thr:
        span = max(start_thr - top_thr, 1.0)
        p = (angle_avg - top_thr) / span
        if p > 0.55:
            tips.append("Вдох: поднимайте обе руки выше синхронно — середина подъёма.")
        elif p > 0.22:
            tips.append("Продолжайте подъём обеими руками на одной высоте.")
        else:
            tips.append("Почти верх цикла — без рывка, плечи не тяните к ушам.")
        return merge_tips(tips, max_items=4)

    if neutral_low <= angle_avg <= neutral_high:
        tips.append("Середина амплитуды — свяжите с вдохом или выдохом, не обрывайте дугу.")
        return merge_tips(tips, max_items=4)

    if phase == "up":
        tips.append("После верха мягко опускайте обе руки вниз в одном темпе.")
    return merge_tips(tips, max_items=4)


def partial_squat_live(
    angle: float,
    phase: str,
    ready: bool,
    rate: float,
) -> list[str]:
    """Советы по углу бедро—колено—щиколотка (совпадает с логикой PartialSquatExercise)."""
    from app.exercises.squat_thresholds import BENT_DROP, RETURN_DROP

    tips = list(speed_tip_deg_s(rate, 80.0))
    if not ready:
        tips.append("Встаньте боком к камере, выпрямите колено — система запомнит стойку.")
    elif phase == "down":
        tips.append("Поднимитесь почти полностью в стойку — повтор засчитается на выпрямлении.")
    elif phase == "up":
        tips.append(f"Доведите колено до стойки (~{RETURN_DROP}° к эталону) после приседа.")
    else:
        tips.append(f"Присядьте глубже (~{BENT_DROP}° сгибания), затем плавно выпрямитесь.")
    return merge_tips(tips, max_items=4)


def knee_extension_live(
    angle: float,
    phase: str,
    ready: bool,
    rate: float,
) -> list[str]:
    """Разгибание колена сидя: малый угол — сгиб, большой — разгиб."""
    bent_thr = 118.0
    extended_thr = 152.0
    tips = list(speed_tip_deg_s(rate, 75.0))

    if not ready:
        if angle > bent_thr + 15:
            tips.append("Согните колено сильнее — для старта нужно положение «нога согнута».")
        elif angle > bent_thr + 4:
            tips.append("Чуть сильнее согните колено — почти готовы к разгибанию.")
        else:
            tips.append("Исход зафиксирован: медленно разгибайте ногу, стопа не отрывается резко от пола.")
        return merge_tips(tips, max_items=4)

    if phase == "down" and angle <= bent_thr + 5:
        tips.append("Из сгиба ведите голень вперёд до почти прямого колена.")
        return merge_tips(tips, max_items=4)

    if phase == "up" and angle >= extended_thr - 8:
        tips.append("Почти прямое колено — плавно согните обратно для следующего повтора.")
        return merge_tips(tips, max_items=4)

    if bent_thr < angle < extended_thr:
        if rate > 50:
            tips.append("Доведите разгибание до конца без рывка — сейчас темп высокий.")
        elif rate < -40:
            tips.append("Не сгибайте колено, пока не разогнули достаточно.")
        else:
            tips.append("Середина разгибания — спина нейтральная, не запрокидывайте корпус.")
    return merge_tips(tips, max_items=4)
