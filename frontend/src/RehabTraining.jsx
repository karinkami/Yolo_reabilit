import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  bundleQueueHint,
  isDualArmExercise,
  isPartialSquat,
  resolveSideImperative,
  resolveSideLabel,
  sideImperative,
  sideLabelFull,
  sidePrepareMessage,
} from "./utils/assignmentSide.js";

const SESSION_ASSIGNMENT_KEY = "rehab_primary_assignment_id";

const PHASE_LABELS = {
  start: "Старт",
  down: "Вниз",
  up: "Вверх",
  waiting_start: "Исходное положение",
  finished: "Завершено",
  neutral: "Середина движения",
};

function url(path, fb) {
  return path && String(path).length ? path : fb;
}

function formatPhase(code) {
  if (!code) return "—";
  return PHASE_LABELS[code] || String(code).replace(/_/g, " ");
}

function classifyCoach(data) {
  const corr = `${data.correctness || ""} ${data.feedback || ""}`;
  const done =
    data.completed === true ||
    data.phase === "finished" ||
    /Упражнение завершено|Цель достигнут|Цель достигла/i.test(corr);
  if (done) return { tone: "done", badge: "Цель выполнена" };

  if (
    /Слишком быстро|Не спешите|Низкая уверенность|Не найден|неуверен|Спешите|нет позы|Ошибка|плохо видны|слишком глубоко|слишком резк|скорректируйте|опустите руку|выпрямите|асимметр|симметр|Вне траектории|Повторите движение|дорожк|не засчитан/i.test(
      corr
    )
  ) {
    return { tone: "warn", badge: "Внимание" };
  }

  if (/Цикл засчитан|хорошо|Готово|Ритм|Фаза|Вдох|Выдох|Ожидание старта|Стартуйте/i.test(data.correctness || "")) {
    return { tone: "ok", badge: "" };
  }

  return { tone: "neutral", badge: "" };
}

const PROFILE_HINT =
  "Встаньте боком к камере: рабочая сторона ближе к объективу, в кадре силуэт корпуса сбоку.";

const EXERCISE_FALLBACK = {
  shoulder_abduction: {
    title: "Отведение руки в сторону",
    hint: `${PROFILE_HINT} Отводите руку в сторону и опускайте вниз полностью.`,
    steps: [],
  },
  recovery_abduction: {
    title: "Лёгкое отведение",
    hint: `${PROFILE_HINT} Короткое отведение в сторону, небольшая амплитуда.`,
    steps: [],
  },
  forward_raise: {
    title: "Подъём руки вперёд",
    hint: `${PROFILE_HINT} Подъём вперёд-вверх от бедра, не в сторону; повтор засчитывается при опускании.`,
    steps: [
      "Встаньте боком к камере: рабочая сторона ближе к объективу, плечо, локоть и кисть в кадре.",
      "Исходное положение: рука опущена вдоль бедра.",
      "Поднимайте руку вперёд и немного вверх (не отводите в сторону от корпуса).",
      "Опускайте руку вниз к бедру плавно — на этом этапе засчитывается повтор.",
    ],
  },
  scaption_raise: {
    title: "Скапционный подъём",
    hint: `${PROFILE_HINT} Дуга между «в сторону» и «вперёд-вверх».`,
    steps: [],
  },
  arm_raise: {
    title: "Подъём руки вверх",
    hint: `${PROFILE_HINT} Поднимайте руку вверх, опускайте вниз плавно.`,
    steps: [],
  },
  breathing_arms: {
    title: "Дыхание с руками",
    hint: "Боком или четвертью поворотом: обе руки в кадре, синхронно вверх/вниз.",
    steps: [],
  },
  breathing_arms_slow: {
    title: "Медленное дыхание с руками",
    hint: "Как дыхание с руками: боком к камере, обе руки видны, темп медленный.",
    steps: [],
  },
  partial_squat: {
    title: "Частичное приседание",
    hint: "Стоя боком (в профиль) к камере. Рабочая нога ближе к объективу — присед и выпрямление.",
    steps: [],
  },
  elbow_flexion: {
    title: "Сгибание в локте",
    hint: `${PROFILE_HINT} Сгибайте и разгибайте локоть, плечо неподвижно.`,
    steps: [],
  },
  knee_extension: {
    title: "Разгибание колена",
    hint: "Сидя боком к камере, рабочая нога в кадре: разгибание и сгиб.",
    steps: [],
  },
};

export default function RehabTraining({ urls = {}, bootstrap = {}, initialAssignmentId = null, embedded = false }) {
  const U = urls;
  const boot = bootstrap || {};
  const personalRecommendations = String(boot.personalRecommendations || "").trim();
  const [planOptions, setPlanOptions] = useState(() =>
    Array.isArray(boot.options) ? boot.options : []
  );
  const options = planOptions;
  const hasAssign = options.length > 0;

  const refreshPlan = useCallback(async () => {
    try {
      const res = await fetch("/patient/rehab/api/bootstrap", { credentials: "same-origin" });
      const data = await res.json();
      if (!data?.ok) return [];
      const next = Array.isArray(data.options) ? data.options : [];
      setPlanOptions(next);
      return next;
    } catch {
      return [];
    }
  }, []);

  const persistId = useCallback((id) => {
    try {
      if (id) sessionStorage.setItem(SESSION_ASSIGNMENT_KEY, String(id));
    } catch (_) {
      /* ignore */
    }
  }, []);

  const [selId, setSelId] = useState(() => {
    try {
      const sid = sessionStorage.getItem(SESSION_ASSIGNMENT_KEY);
      if (!sid || !options.length) return String(options[0]?.primary_id ?? "");
      const ok = options.some((o) => String(o.primary_id) === sid);
      return ok ? sid : String(options[0].primary_id);
    } catch (_) {
      return String(options[0]?.primary_id ?? "");
    }
  });

  const [queueIndex, setQueueIndex] = useState(0);

  useEffect(() => {
    if (initialAssignmentId == null || !options.length) return;
    const idStr = String(initialAssignmentId);
    if (!options.some((o) => String(o.primary_id) === idStr)) return;
    setSelId(idStr);
    persistId(idStr);
    setQueueIndex(0);
  }, [initialAssignmentId, options, persistId]);

  const [guides, setGuides] = useState({});

  const currentOpt = useMemo(
    () => options.find((o) => String(o.primary_id) === String(selId)) || options[0] || null,
    [options, selId]
  );

  const assignmentQueue = useMemo(() => {
    if (!currentOpt?.assignments_payload) return [];
    return Array.isArray(currentOpt.assignments_payload) ? currentOpt.assignments_payload : [];
  }, [currentOpt]);

  const bundleMode = currentOpt?.bundle_mode === true || assignmentQueue.length > 1;
  const bundleSidesTotal = bundleMode
    ? Number(currentOpt?.sides_total || assignmentQueue.length || 2)
    : 1;
  const bundleSidesDone = bundleMode ? Number(currentOpt?.sides_done || 0) : 0;
  const bundleProgressLabel =
    currentOpt?.bundle_progress_label || (bundleMode ? `${bundleSidesDone}/${bundleSidesTotal}` : "");

  const effectiveQueueIndex = useMemo(() => {
    if (!bundleMode || bundleSidesDone <= 0) return queueIndex;
    if (bundleSidesDone >= bundleSidesTotal) return queueIndex;
    const rec = Number(currentOpt?.recommended_queue_index);
    return Number.isFinite(rec) ? rec : bundleSidesDone;
  }, [
    bundleMode,
    bundleSidesDone,
    bundleSidesTotal,
    queueIndex,
    currentOpt?.recommended_queue_index,
  ]);

  const queueItem = assignmentQueue[effectiveQueueIndex] ?? assignmentQueue[0] ?? null;
  const dualBreathing = currentOpt?.dual_breathing === true;
  const showSide = !bundleMode && !dualBreathing;
  const exerciseKey = currentOpt?.exercise_key || "shoulder_abduction";

  useEffect(() => {
    if (!bundleMode || !currentOpt) return;
    if (bundleSidesDone > 0 && bundleSidesDone < bundleSidesTotal) {
      const rec = Number(currentOpt.recommended_queue_index);
      if (Number.isFinite(rec) && rec !== queueIndex) {
        setQueueIndex(rec);
      }
    } else if (bundleSidesDone === 0 && queueIndex !== 0) {
      setQueueIndex(0);
    }
  }, [selId, bundleMode, bundleSidesDone, bundleSidesTotal, currentOpt?.recommended_queue_index]);

  const [side, setSide] = useState(queueItem?.side || "left");
  const [repsTarget, setRepsTarget] = useState(queueItem?.target_reps ?? 10);

  const activeSideLabel = useMemo(() => {
    if (dualBreathing || isDualArmExercise(exerciseKey)) return "Обе руки";
    if (!queueItem) return "";
    if (isPartialSquat(exerciseKey)) {
      return bundleQueueHint(
        effectiveQueueIndex,
        assignmentQueue.length,
        queueItem.side || "left",
        exerciseKey
      );
    }
    return (
      resolveSideLabel(queueItem.side || "left", exerciseKey, queueItem.side_label) ||
      bundleQueueHint(
        effectiveQueueIndex,
        assignmentQueue.length,
        queueItem.side || "left",
        exerciseKey
      )
    );
  }, [dualBreathing, exerciseKey, queueItem, effectiveQueueIndex, assignmentQueue.length]);

  const sideCoachLine = useMemo(() => {
    if (dualBreathing || isDualArmExercise(exerciseKey)) {
      return "Двигайте обе руки синхронно — так назначил врач.";
    }
    if (isPartialSquat(exerciseKey)) {
      const line = resolveSideImperative(
        queueItem?.side || side,
        exerciseKey,
        queueItem?.side_imperative
      );
      if (bundleMode && queueItem && bundleSidesTotal > 1) {
        const ord = effectiveQueueIndex + 1;
        const prog =
          bundleSidesDone > 0 && bundleSidesDone < bundleSidesTotal
            ? ` • прогресс ${bundleProgressLabel}`
            : "";
        return `${line} (${ord} из ${bundleSidesTotal})${prog}.`;
      }
      return line;
    }
    if (bundleMode && queueItem) {
      const ord = effectiveQueueIndex + 1;
      const label = resolveSideLabel(
        queueItem.side || "left",
        exerciseKey,
        queueItem.side_label
      );
      const prog =
        bundleSidesDone > 0 && bundleSidesDone < bundleSidesTotal
          ? ` • прогресс ${bundleProgressLabel}`
          : "";
      return `Сейчас: ${label} (${ord} из ${bundleSidesTotal})${prog}.`;
    }
    if (showSide && queueItem) {
      return resolveSideImperative(queueItem.side || side, exerciseKey, queueItem.side_imperative);
    }
    return "";
  }, [
    dualBreathing,
    exerciseKey,
    bundleMode,
    queueItem,
    effectiveQueueIndex,
    bundleSidesDone,
    bundleSidesTotal,
    bundleProgressLabel,
    assignmentQueue.length,
    showSide,
    side,
  ]);

  const [sessionLabel, setSessionLabel] = useState("Сессия неактивна");
  const [sessionActiveUi, setSessionActiveUi] = useState(false);

  const [feedback, setFeedback] = useState(
    hasAssign ? "Назначение загружено. Зайдите в кадр и нажмите «Начать подход»." : "Нет назначений от врача."
  );
  const [coachTone, setCoachTone] = useState("neutral");
  const [coachBadge, setCoachBadge] = useState("");

  const [angleDisp, setAngleDisp] = useState("—");
  const [phaseDisp, setPhaseDisp] = useState("—");
  const [repsStr, setRepsStr] = useState(hasAssign ? `0 / ${queueItem?.target_reps ?? 10}` : "0 / —");
  const [correctnessDisp, setCorrectnessDisp] = useState("—");
  const [videoSrc, setVideoSrc] = useState("");
  const [showVid, setShowVid] = useState(false);

  const [bundMsg, setBundMsg] = useState("");

  const feedbackTimer = useRef(null);
  const completionSaveSent = useRef(false);
  const handlingFinish = useRef(false);
  const videoRetryRef = useRef(0);
  useEffect(() => {
    const gUrl = url(U.guides, "");
    if (!gUrl || !hasAssign) return;
    fetch(gUrl, { credentials: "same-origin" })
      .then((r) => r.json())
      .then((d) => typeof d === "object" && d && setGuides(d))
      .catch(() => setGuides({}));
  }, [hasAssign, U.guides]);

  const instructionBlock = useMemo(() => {
    const g = guides[exerciseKey];
    const fb = EXERCISE_FALLBACK[exerciseKey] || EXERCISE_FALLBACK.shoulder_abduction;
    const steps =
      Array.isArray(g?.how_to) && g.how_to.length
        ? g.how_to
        : fb.steps?.length
          ? fb.steps
          : ["Следуйте блоку «Сейчас» и «Советы» справа — они обновляются по камере."];
    const mistakes = Array.isArray(g?.mistakes) ? g.mistakes.filter((x) => String(x).trim()) : [];
    return {
      title: g?.title || fb.title,
      hint: g?.summary || fb.hint,
      whatCounts: String(g?.what_counts || "").trim(),
      mistakes,
      steps,
    };
  }, [guides, exerciseKey]);

  useEffect(() => {
    if (!queueItem) return;
    setSide(queueItem.side || "left");
    setRepsTarget(queueItem.target_reps ?? 10);
    setRepsStr(`0 / ${queueItem.target_reps ?? 10}`);
    if (showSide || bundleMode) {
      setFeedback(sidePrepareMessage(queueItem.side || "left", exerciseKey));
    }
  }, [
    queueIndex,
    selId,
    queueItem?.id,
    queueItem?.side,
    queueItem?.target_reps,
    exerciseKey,
    showSide,
    bundleMode,
  ]);

  const applyPresentation = useCallback((data) => {
    const c = classifyCoach(data);
    setCoachTone(c.tone);
    setCoachBadge(c.badge || "");
  }, []);

  const selectExerciseReq = useCallback(
    async (item) => {
      const row = item || queueItem;
      if (!row?.id) return null;
      const res = await fetch(url(U.selectExercise, "/select_exercise"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ assignment_id: Number(row.id) }),
      });
      const data = await res.json().catch(() => ({}));
      if (data.status === "ok") {
        if (data.side) setSide(data.side);
        if (data.target_reps != null) {
          setRepsTarget(data.target_reps);
          setRepsStr(`0 / ${data.target_reps}`);
        }
      }
      return data;
    },
    [queueItem, U.selectExercise]
  );

  const applySettingsReq = useCallback(
    async (item) => {
      if (!hasAssign) return;
      const row = item || queueItem;
      await selectExerciseReq(row);
      const sidePost = row?.side || side || "left";
      await fetch(url(U.settings, "/api/settings"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ side: sidePost }),
      });
    },
    [hasAssign, queueItem, side, selectExerciseReq, U.settings]
  );

  const startTrainingForItem = useCallback(
    async (item) => {
      const row = item || queueItem;
      if (!row?.id) return;

      completionSaveSent.current = false;
      setBundMsg("");
      stopIntervals();
      setShowVid(false);
      setVideoSrc("");
      videoRetryRef.current = 0;
      await new Promise((r) => setTimeout(r, 280));

      await applySettingsReq(row);
      const startRes = await fetch(url(U.start, "/api/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ assignment_id: Number(row.id) }),
      });
      const startData = await startRes.json().catch(() => ({}));
      if (!startRes.ok || startData.status === "error") {
        setSessionActiveUi(false);
        setShowVid(false);
        setVideoSrc("");
        setFeedback(startData.message || "Не удалось начать подход. Обновите страницу и выберите назначение.");
        setCorrectnessDisp("Ошибка");
        applyPresentation({ session_active: false, correctness: "Ошибка" });
        return;
      }

      handlingFinish.current = false;
      const exKey = currentOpt?.exercise_key || exerciseKey;
      const coach = resolveSideImperative(row.side || "left", exKey, row.side_imperative);

      let sessionOk = false;
      try {
        const fbRes = await fetch(url(U.feedback, "/api/feedback"), {
          cache: "no-store",
          credentials: "same-origin",
        });
        if (fbRes.ok) {
          const fb = await fbRes.json();
          sessionOk = fb.session_active === true && fb.selected_exercise === exKey;
        }
      } catch {
        sessionOk = false;
      }
      if (!sessionOk) {
        setSessionActiveUi(false);
        setShowVid(false);
        setVideoSrc("");
        setFeedback(
          "Сессия не активировалась. Нажмите «Остановить», подождите 2 секунды и снова «Начать подход»."
        );
        setCorrectnessDisp("Ошибка");
        applyPresentation({ session_active: false, correctness: "Ошибка" });
        return;
      }

      setSessionActiveUi(true);
      setSessionLabel("Идёт подход");
      setShowVid(true);
      videoRetryRef.current = 0;
      const gen = startData.stream_gen != null ? `&g=${startData.stream_gen}` : "";
      setVideoSrc(`${url(U.videoFeed, "/video_feed")}?t=${Date.now()}${gen}`);
      setFeedback(`${coach} Подстраивайте движение по блоку «Сейчас».`);
      setCorrectnessDisp("Подготовка");
      setAngleDisp("0°");
      setPhaseDisp(formatPhase("start"));
      setRepsStr(`0 / ${row.target_reps ?? repsTarget ?? 10}`);
      applyPresentation({ session_active: true, phase: "start", correctness: "Подготовка" });

      feedbackTimer.current = setInterval(fetchFeedbackTick, 280);
    },
    [
      queueItem,
      currentOpt,
      exerciseKey,
      repsTarget,
      applySettingsReq,
      U.start,
      U.videoFeed,
      applyPresentation,
    ]
  );

  useEffect(() => {
    if (!hasAssign || !queueItem?.id) return;
    persistId(selId);
    applySettingsReq().catch(() => {});
  }, [selId, queueIndex, hasAssign, bundleMode, dualBreathing, queueItem?.id, persistId, applySettingsReq]);

  const saveCompletionReq = async (data, assignmentId) => {
    const endpoint = url(U.complete, "/api/complete");
    const aid = assignmentId ?? queueItem?.id ?? selId;
    const target = Math.max(1, Number(data.target_reps ?? repsTarget ?? 10) || 10);
    const rawReps = Math.max(0, Number(data.reps ?? 0) || 0);
    const reps =
      data.completed === true || data.phase === "finished"
        ? Math.max(rawReps, target)
        : rawReps;
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          assignment_id: aid != null && aid !== "" ? Number(aid) : undefined,
          exercise_key: exerciseKey,
          reps,
          target_reps: target,
          correctness: data.correctness ?? "",
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        return { ...body, status: body.status || "error" };
      }
      return body;
    } catch {
      return {};
    }
  };

  const pickNextPlanSelection = useCallback((refreshed, nextAssignmentId) => {
    if (!refreshed?.length) {
      return { sel: "", queueIdx: 0 };
    }
    if (nextAssignmentId != null) {
      const idStr = String(nextAssignmentId);
      for (const opt of refreshed) {
        const payload = opt.assignments_payload || [];
        const qi = payload.findIndex((a) => String(a.id) === idStr);
        if (qi >= 0) {
          return { sel: String(opt.primary_id), queueIdx: qi };
        }
      }
    }
    return { sel: String(refreshed[0].primary_id), queueIdx: 0 };
  }, []);

  const stopIntervals = () => {
    if (feedbackTimer.current) {
      clearInterval(feedbackTimer.current);
      feedbackTimer.current = null;
    }
  };

  const finishVideoShellLocal = () => {
    stopIntervals();
    setVideoSrc("");
    setShowVid(false);
  };

  const fetchFeedbackTick = async () => {
    try {
      const res = await fetch(url(U.feedback, "/api/feedback"), {
        cache: "no-store",
        credentials: "same-origin",
      });
      if (!res.ok) return;
      const data = await res.json();
      const camOn = data.session_active === true;

      setFeedback(data.feedback ?? "…");
      if (camOn) {
        setAngleDisp(`${Math.round(data.angle ?? 0)}°`);
        setPhaseDisp(formatPhase(data.phase));
      } else if (data.phase === "finished") {
        setAngleDisp("—");
        setPhaseDisp(formatPhase("finished"));
      } else {
        setAngleDisp("—");
        setPhaseDisp("—");
      }

      setRepsStr(`${data.reps ?? 0} / ${data.target_reps ?? 10}`);
      setCorrectnessDisp(data.correctness ?? "—");
      applyPresentation(data);

      const finished =
        data.completed === true || (data.session_active === false && data.phase === "finished");
      if (!finished) return;

      if (handlingFinish.current) return;
      handlingFinish.current = true;

      stopIntervals();

      const finishedAssignmentId = queueItem?.id;

      let saveRes = {};
      if (!completionSaveSent.current && hasAssign) {
        completionSaveSent.current = true;
        saveRes = await saveCompletionReq(data, finishedAssignmentId);
      }

      const refreshed = await refreshPlan();
      const stillInPlan = refreshed.some((o) => String(o.primary_id) === String(selId));
      const updatedOpt = stillInPlan
        ? refreshed.find((o) => String(o.primary_id) === String(selId)) ||
          refreshed.find((o) => o.exercise_key === exerciseKey) ||
          null
        : null;
      const sidesTotal = updatedOpt
        ? Number(updatedOpt.sides_total || 2)
        : bundleSidesTotal;
      const sidesDone = updatedOpt ? Number(updatedOpt.sides_done || 0) : bundleSidesDone + 1;
      const progressLabel = updatedOpt?.bundle_progress_label || `${sidesDone}/${sidesTotal}`;
      const nextSideLabel = updatedOpt?.next_side_label || "";
      const hasMoreSides = bundleMode && sidesDone < sidesTotal;

      if (hasMoreSides) {
        const finishedLabel = resolveSideLabel(
          queueItem?.side || "right",
          exerciseKey,
          queueItem?.side_label
        );

        finishVideoShellLocal();
        setSessionActiveUi(false);
        setSessionLabel(`Выполнено ${progressLabel}`);

        if (updatedOpt && refreshed.some((o) => String(o.primary_id) === String(selId))) {
          const rec = Number(updatedOpt.recommended_queue_index);
          if (Number.isFinite(rec)) setQueueIndex(rec);
        }

        setBundMsg(
          `${finishedLabel} — ${progressLabel}. Дальше ${nextSideLabel || "вторая сторона"}: снова это упражнение и «Начать подход», или выберите другое из списка.`
        );
        setFeedback(
          `Подход сохранён (${progressLabel}). Можно продолжить это упражнение или выбрать другое.`
        );
        setAngleDisp("—");
        setPhaseDisp(formatPhase("waiting_start"));
        setCorrectnessDisp("Готово");

        completionSaveSent.current = false;
        handlingFinish.current = false;
        return;
      }

      const removed =
        saveRes?.assignment_completed === true || !stillInPlan;
      const { sel, queueIdx } = pickNextPlanSelection(refreshed, null);
      if (removed) {
        if (sel) {
          setSelId(sel);
          setQueueIndex(queueIdx);
          persistId(sel);
        } else {
          setSelId("");
          setQueueIndex(0);
        }
      }

      finishVideoShellLocal();
      applyPresentation({
        ...data,
        completed: true,
        session_active: false,
        phase: "finished",
      });
      setSessionActiveUi(false);
      const doneCount = refreshed?.length ?? 0;
      const summary = saveRes?.correctness_summary || "";
      setSessionLabel(doneCount ? "Упражнение завершено" : "Все назначения выполнены");
      setBundMsg(
        removed
          ? summary
            ? `${summary} Сохранено в статистику. Упражнение убрано из списка.`
            : "Результат сохранён в статистику. Упражнение убрано из списка."
          : doneCount
            ? "Подход сохранён. Выберите следующее упражнение в списке."
            : "Все упражнения от врача выполнены."
      );
      setAngleDisp("—");
      setPhaseDisp(formatPhase("finished"));
      completionSaveSent.current = false;
      handlingFinish.current = false;
    } catch {
      handlingFinish.current = false;
    }
  };

  const startTraining = async () => {
    if (!hasAssign) return;
    await startTrainingForItem(queueItem);
  };

  const stopTraining = async () => {
    stopIntervals();
    finishVideoShellLocal();
    videoRetryRef.current = 0;

    let snap = { reps: 0, target_reps: repsTarget ?? 10, correctness: "" };
    try {
      const res = await fetch(url(U.feedback, "/api/feedback"), {
        cache: "no-store",
        credentials: "same-origin",
      });
      if (res.ok) snap = await res.json();
    } catch {
      /* последний снимок с сервера необязателен */
    }

    const repsDone = Math.max(0, parseInt(String(snap.reps ?? 0), 10) || 0);
    const target = Math.max(1, parseInt(String(snap.target_reps ?? repsTarget ?? 10), 10) || 10);

    let stopData = {};
    try {
      const res = await fetch(url(U.stop, "/api/stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          reps: repsDone,
          target_reps: target,
          correctness: snap.correctness ?? "",
        }),
      });
      stopData = await res.json().catch(() => ({}));
    } catch {
      stopData = {};
    }

    setSessionActiveUi(false);
    completionSaveSent.current = false;
    setAngleDisp("—");
    setPhaseDisp("—");

    const saved = stopData.saved === true;
    const savedReps = saved ? stopData.reps_completed ?? repsDone : repsDone;
    const savedTarget = saved ? stopData.target_reps ?? target : target;
    const bundleLbl = saved ? String(stopData.bundle_progress_label || "").trim() : "";
    const summary = saved ? String(stopData.correctness_summary || "").trim() : "";

    if (saved) {
      const refreshed = await refreshPlan();
      const updatedOpt =
        refreshed.find((o) => String(o.primary_id) === String(selId)) ||
        refreshed.find((o) => o.exercise_key === exerciseKey) ||
        null;
      const progressLabel = bundleLbl || updatedOpt?.bundle_progress_label || "";
      const repsLine = `${savedReps}/${savedTarget} повт.`;
      const scoreLine =
        stopData.score_percent != null ? ` · ${stopData.score_percent}%` : "";

      setSessionLabel(progressLabel ? `Остановлено (${progressLabel})` : "Подход остановлен");
      setRepsStr(`${savedReps} / ${savedTarget}`);
      setCorrectnessDisp(summary || "Сохранено в статистике");
      setFeedback(
        progressLabel
          ? `Подход сохранён: ${repsLine}${scoreLine}. Прогресс связки ${progressLabel} — назначение остаётся, можно продолжить позже.`
          : `Подход сохранён: ${repsLine}${scoreLine}. Результат есть в статистике; назначение остаётся — нажмите «Начать подход», когда будете готовы.`
      );
      applyPresentation({
        session_active: false,
        correctness: summary || "Подход остановлен",
        reps: savedReps,
        target_reps: savedTarget,
      });
    } else {
      setSessionLabel("Подход остановлен");
      setRepsStr(`${repsDone} / ${target}`);
      setCorrectnessDisp("—");
      setFeedback(
        stopData.message ||
          "Подход остановлен. Результат не записан — попробуйте снова или дождитесь автосохранения при достижении цели."
      );
      applyPresentation({ session_active: false });
    }
  };

  const onSelExercise = async (ev) => {
    const id = ev.target.value;
    setSelId(id);
    setQueueIndex(0);
    setBundMsg("");
    persistId(id);
  };

  useEffect(() => () => stopIntervals(), []);

  if (!hasAssign) {
    return (
      <div className={`rehab-app${embedded ? " rehab-app--embedded" : ""}`}>
        <div className="rehab-pane">
          <h2>Пока нет назначений</h2>
          <p className="rehab-muted">Врач добавит упражнения в кабинет — они появятся на главной странице.</p>
        </div>
      </div>
    );
  }

  const panelClass =
    coachTone === "warn"
      ? "rehab-feedback-warn"
      : coachTone === "ok"
        ? "rehab-feedback-ok"
        : coachTone === "done"
          ? "rehab-feedback-done"
          : "rehab-feedback-neutral";

  return (
    <div className={`rehab-app${embedded ? " rehab-app--embedded" : ""}`}>
      {!embedded ? (
        <header className="rehab-hero">
          <div>
            <h1 className="rehab-title">Тренировка</h1>
          </div>
          <span className={`rehab-session-badge ${sessionActiveUi ? "active" : "idle"}`}>{sessionLabel}</span>
        </header>
      ) : (
        <div className="rehab-session-bar">
          <span className="rehab-session-bar__label">Статус подхода</span>
          <span className={`rehab-session-badge ${sessionActiveUi ? "active" : "idle"}`}>{sessionLabel}</span>
        </div>
      )}

      {options.length > 0 ? (
        <section className="rehab-plan-panel ui-lift" aria-label="План упражнений от врача">
          <h2 className="rehab-plan-panel__title">Что нужно выполнить</h2>
          <p className="rehab-plan-panel__lead muted">
            Выберите пункт в списке или в поле «Назначение» ниже — затем «Начать подход».
          </p>
          <ol className="rehab-plan-panel__list">
            {options.map((o, idx) => {
              const active = String(o.primary_id) === String(selId);
              return (
                <li key={o.primary_id} className={`rehab-plan-panel__item${active ? " is-current" : ""}`}>
                  <span className="rehab-plan-panel__num">{idx + 1}</span>
                  <button
                    type="button"
                    className="rehab-plan-panel__pick"
                    onClick={() => {
                      setSelId(String(o.primary_id));
                      setQueueIndex(0);
                      persistId(o.primary_id);
                    }}
                  >
                    <span className="rehab-plan-panel__label">{o.label_line || o.short_label}</span>
                    {o.bundle_progress_label ? (
                      <span className="rehab-plan-panel__hint">Прогресс: {o.bundle_progress_label}</span>
                    ) : null}
                    {o.bundle_hint ? <span className="rehab-plan-panel__hint">{o.bundle_hint}</span> : null}
                  </button>
                </li>
              );
            })}
          </ol>
        </section>
      ) : null}

      <section className="rehab-cards">
        {personalRecommendations ? (
          <aside className="rehab-pane rehab-personal-rec ui-lift" aria-label="Рекомендации врача">
            <h2 className="rehab-personal-rec__title">От врача</h2>
            <p className="rehab-personal-rec__body">{personalRecommendations}</p>
          </aside>
        ) : null}

        <div className="rehab-meta-row">
        <div className="rehab-pane rehab-pane--instruction ui-lift">
          <span className="rehab-feedback-kicker">Инструкция</span>
          <h2>{instructionBlock.title}</h2>
          {sideCoachLine ? (
            <p className="rehab-side-callout" role="status">
              <span className="rehab-side-callout__badge">{activeSideLabel || "Сторона"}</span>
              {sideCoachLine}
            </p>
          ) : null}
          <p className="rehab-muted" style={{ fontSize: "1.12rem", lineHeight: 1.55 }}>
            {instructionBlock.hint}
          </p>
          {instructionBlock.whatCounts ? (
            <div className="rehab-instruction-meta" role="note">
              <span className="rehab-instruction-meta__label">Что считается повтором</span>
              <p className="rehab-instruction-meta__text">{instructionBlock.whatCounts}</p>
            </div>
          ) : null}
          <ol className="instruction-steps">
            {instructionBlock.steps.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ol>
          {instructionBlock.mistakes?.length ? (
            <div className="rehab-instruction-warn">
              <span className="rehab-instruction-meta__label">Типичные ошибки</span>
              <ul className="rehab-mistakes-list">
                {instructionBlock.mistakes.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        <div className="rehab-pane rehab-pane--setup ui-lift">
          <span className="rehab-feedback-kicker">Подход</span>
          <h2>
            {currentOpt.short_label}
            {bundleProgressLabel && bundleMode ? ` (${bundleProgressLabel})` : ""}
          </h2>
          <div className="rehab-form-grid">
            <label className="rehab-field">
              Назначение
              <select value={selId} onChange={onSelExercise}>
                {options.map((o) => (
                  <option key={o.primary_id} value={String(o.primary_id)}>
                    {o.short_label}
                  </option>
                ))}
              </select>
            </label>

            {!showSide && !bundleMode ? null : dualBreathing ? null : (
              <div className="rehab-field rehab-field-readonly">
                <span className="rehab-field-label">{bundleMode ? "Сейчас в очереди" : "Сторона (от врача)"}</span>
                <div className="rehab-readonly-value rehab-readonly-value--side" title="Задано врачом">
                  {activeSideLabel || (side === "right" ? "Правая" : "Левая")}
                </div>
              </div>
            )}
            {bundleMode && currentOpt?.bundle_hint ? (
              <div className="rehab-field rehab-field-readonly rehab-field--full">
                <span className="rehab-field-label">Очередь</span>
                <div className="rehab-readonly-value" title="Задано врачом">
                  {currentOpt.bundle_hint}
                </div>
              </div>
            ) : null}

            <div className="rehab-field rehab-field-readonly">
              <span className="rehab-field-label">Повторов за подход</span>
              <div className="rehab-readonly-value" title="Задано врачом">
                {repsTarget}
              </div>
            </div>
          </div>

          {bundMsg ? <div className="rehab-banner">{bundMsg}</div> : null}

          <div className="rehab-buttons" style={{ marginTop: "1rem" }}>
            {sessionActiveUi ? (
              <button type="button" className="rehab-btn rehab-btn-danger" onClick={stopTraining}>
                Остановить
              </button>
            ) : (
              <button type="button" className="rehab-btn rehab-btn-primary" onClick={startTraining}>
                Начать подход
              </button>
            )}
          </div>
        </div>
        </div>

        <div className="rehab-pane rehab-pane--workout ui-lift">
          <div className="rehab-workout-head">
            <span className="rehab-feedback-kicker">Выполнение</span>
            <h2 className="rehab-workout-col__title">Выполнение упражнения</h2>
          </div>
          <div className={`rehab-workout-layout${embedded ? " rehab-workout-layout--patient" : ""}`}>
            <div className="rehab-workout-col rehab-workout-col--video">
              <span className="rehab-feedback-kicker rehab-video-kicker">Камера</span>
              <div className="rehab-video-box" aria-label="Видео с камеры">
                {!showVid || !videoSrc ? (
                  <div className="rehab-ph">
                    <div className="rehab-ph-title">Пауза</div>
                    <div className="rehab-ph-sub">«Начать подход»</div>
                  </div>
                ) : (
                  <img
                    src={videoSrc}
                    alt="Ваше изображение с камеры"
                    className="rehab-video"
                    onError={() => {
                      if (videoRetryRef.current >= 2) {
                        setFeedback(
                          "Камера не отображается. Нажмите «Остановить», подождите 2 с и снова «Начать подход». Закройте другие программы с веб-камерой."
                        );
                        return;
                      }
                      videoRetryRef.current += 1;
                      const sep = videoSrc.includes("?") ? "&" : "?";
                      setVideoSrc(`${videoSrc}${sep}retry=${videoRetryRef.current}&t=${Date.now()}`);
                    }}
                  />
                )}
              </div>
            </div>

            <div className="rehab-workout-col rehab-workout-col--side">
              <div className="rehab-live-stack">
                <div className={`rehab-feedback ${panelClass}`}>
                  <div className="rehab-feedback-head">
                    <span className="rehab-feedback-kicker">Сейчас</span>
                    {activeSideLabel && !dualBreathing ? (
                      <span className="rehab-side-badge" title="Сторона по назначению врача">
                        {activeSideLabel}
                      </span>
                    ) : null}
                    {coachBadge ? <span className="rehab-feedback-badge">{coachBadge}</span> : null}
                  </div>
                  <p className="rehab-feedback-text">{feedback}</p>
                </div>

                <div className="rehab-side-card rehab-stat-pane">
                  <div className="rehab-feedback-kicker">Повторы</div>
                  <div className="rehab-progress-big">{repsStr}</div>
                  <div className="rehab-stat-grid">
                    {activeSideLabel ? (
                      <div className="rehab-stat-row rehab-stat-row--side">
                        <span>Сторона</span>
                        <strong>{activeSideLabel}</strong>
                      </div>
                    ) : null}
                    <div className="rehab-stat-row">
                      <span>Угол</span>
                      <strong>{angleDisp}</strong>
                    </div>
                    <div className="rehab-stat-row">
                      <span>Фаза</span>
                      <strong>{phaseDisp}</strong>
                    </div>
                    <div className="rehab-stat-row">
                      <span>Статус</span>
                      <strong>{correctnessDisp}</strong>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>

      </section>
    </div>
  );
}
