
import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useSession } from "../hooks/SessionContext.jsx";
import TrainingStats from "../components/TrainingStats.jsx";
import { Breadcrumbs, PageLoading, StatusBanner } from "../components/ui/PagePrimitives.jsx";
import {
  filterAssignmentComplexes,
  filterDoctorExercises,
  isAllowedComplexId,
} from "../constants/assignmentComplexes.js";
import { bothSidesAssignLabel, complexComposeSideHint, isDualArmExercise } from "../utils/assignmentSide.js";
import { parseUtcIso } from "../utils/dateTime.js";

function formatShortDate(iso) {
  const d = parseUtcIso(iso);
  if (!d) return "—";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

function formatBirthInput(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  } catch {
    return "";
  }
}

export default function DoctorPatientPage() {
  const { patientId } = useParams();
  const id = Number(patientId);
  const { user, loading: sessionLoading } = useSession();
  const [data, setData] = useState(null);
  const [fullNameOfficial, setFullNameOfficial] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [comorbidities, setComorbidities] = useState("");
  const [notes, setNotes] = useState("");
  const [exerciseId, setExerciseId] = useState("");
  const [side, setSide] = useState("left");
  const [bothArms, setBothArms] = useState(false);
  const [targetReps, setTargetReps] = useState(10);
  const [complexId, setComplexId] = useState("");
  const [complexBusy, setComplexBusy] = useState(false);
  const [assignMode, setAssignMode] = useState("complex");
  const [msg, setMsg] = useState("");

  const load = () => {
    fetch(`/api/doctor/patient/${id}`, { credentials: "same-origin", cache: "no-store" })
      .then(async (r) => {
        const body = await r.json().catch(() => ({}));
        if (!r.ok) {
          const err = new Error(body.error || `Ошибка ${r.status}`);
          err.status = r.status;
          throw err;
        }
        return body;
      })
      .then((d) => {
        setData(d);
        const p = d.profile || {};
        setFullNameOfficial(p.full_name_official || "");
        setBirthDate(formatBirthInput(p.birth_date));
        setDiagnosis(p.diagnosis || "");
        setComorbidities(p.comorbidities || "");
        setNotes(p.notes || "");
      })
      .catch((e) => setData({ ok: false, loadError: e?.message || "Ошибка загрузки" }));
  };

  const doctorExercises = useMemo(() => filterDoctorExercises(data?.exercises), [data?.exercises]);

  const assignmentComplexes = useMemo(
    () => filterAssignmentComplexes(data?.assignment_complexes),
    [data?.assignment_complexes]
  );

  const selectedComplex = useMemo(
    () => assignmentComplexes.find((c) => c.id === complexId) || null,
    [assignmentComplexes, complexId]
  );

  const hasComplexes = assignmentComplexes.length > 0;

  useEffect(() => {
    if (data?.ok && doctorExercises.length) {
      setExerciseId((prev) => {
        if (prev && doctorExercises.some((e) => String(e.id) === String(prev))) return prev;
        return String(doctorExercises[0].id);
      });
    }
  }, [data, doctorExercises]);

  useEffect(() => {
    if (Number.isFinite(id)) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- перезагрузка только по id
  }, [id]);

  const selectedEx = useMemo(
    () => doctorExercises.find((e) => String(e.id) === String(exerciseId)),
    [doctorExercises, exerciseId]
  );
  const isDualArm = selectedEx?.key === "breathing_arms" || selectedEx?.key === "breathing_arms_slow";
  const isLegEx = selectedEx?.key === "partial_squat";

  const exercisesByGroup = useMemo(() => {
    const groups = data?.clinical_groups;
    const list = doctorExercises;
    if (!groups?.length) return null;
    return groups
      .map((g) => ({ ...g, exercises: list.filter((e) => e.clinical_group === g.id) }))
      .filter((g) => g.exercises.length > 0);
  }, [data, doctorExercises]);

  useEffect(() => {
    if (complexId && !isAllowedComplexId(complexId)) setComplexId("");
  }, [complexId]);

  useEffect(() => {
    if (isDualArm) setBothArms(false);
  }, [isDualArm]);

  const assignView = hasComplexes ? assignMode : "single";

  if (sessionLoading) {
    return (
      <div className="page-shell">
        <PageLoading />
      </div>
    );
  }

  if (user?.role && user.role !== "doctor") {
    return <Navigate to="/patient/" replace />;
  }

  if (data && data.ok === false && !data.loadError) {
    return <Navigate to="/doctor/" replace />;
  }

  if (data?.loadError) {
    return (
      <div className="page-shell doctor-patient-page">
        <p className="body-text" style={{ color: "var(--ui-danger)" }}>
          {data.loadError}
        </p>
        <Link className="btn btn-secondary" to="/doctor/">
          К списку пациентов
        </Link>
      </div>
    );
  }

  if (!data?.ok) {
    return (
      <div className="page-shell">
        <PageLoading label="Загрузка карточки…" />
      </div>
    );
  }

  const prof = data.profile || {};

  const saveProfile = async (e) => {
    e.preventDefault();
    setMsg("");
    const res = await fetch(`/api/doctor/patient/${id}/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        full_name_official: fullNameOfficial,
        birth_date: birthDate || null,
        diagnosis,
        comorbidities,
        notes,
      }),
    });
    if (res.ok) {
      setMsg("Карточка сохранена.");
      load();
    } else setMsg("Не удалось сохранить.");
  };

  const assign = async (e) => {
    e.preventDefault();
    setMsg("");
    const res = await fetch(`/api/doctor/patient/${id}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        exercise_id: Number(exerciseId),
        side,
        target_reps: Number(targetReps),
        both_arms: bothArms && !isDualArm,
      }),
    });
    if (res.ok) {
      setMsg("Назначение добавлено.");
      load();
    } else {
      const j = await res.json().catch(() => ({}));
      setMsg(j.error || "Ошибка назначения.");
    }
  };

  const deactivate = async (row) => {
    if (!window.confirm("Снять это назначение?")) return;
    const body =
      row.type === "pair" ? { assignment_group_id: row.group_id } : { assignment_id: row.ids[0] };
    const res = await fetch(`/api/doctor/patient/${id}/deactivate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      setMsg("Назначение снято.");
      load();
    }
  };

  const showSideField = !(bothArms && !isDualArm);

  const assignComplex = async () => {
    if (!complexId) {
      setMsg("");
      return;
    }
    setComplexBusy(true);
    setMsg("");
    const res = await fetch(`/api/doctor/patient/${id}/assign-complex`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ complex_id: complexId }),
    });
    const j = await res.json().catch(() => ({}));
    setComplexBusy(false);
    if (!res.ok) {
      setMsg(j.error || "Не удалось назначить комплекс.");
      return;
    }
    const composition = selectedComplex?.items_summary;
    setMsg(
      composition
        ? `Комплекс «${j.complex_label || selectedComplex?.label}» назначен (${j.assigned_count} записей): ${composition}.`
        : `Комплекс «${j.complex_label || selectedComplex?.label}» назначен: ${j.assigned_count} записей в кабинете пациента.`
    );
    setComplexId("");
    load();
  };

  const ageStr = prof.age_years != null ? `${prof.age_years} лет` : "—";
  const patientName = prof.full_name_display || data.patient.full_name;

  return (
    <div className="page-shell doctor-patient-page">
      <Breadcrumbs items={[{ label: "Пациенты", to: "/doctor/" }, { label: patientName }]} />

      <header className="doctor-emr-header ui-lift">
        <div className="doctor-emr-header__top">
          <div className="doctor-emr-header__lead">
            <p className="doctor-emr-kicker">Карточка</p>
            <h1 className="doctor-emr-fio">{patientName}</h1>
          </div>
        </div>
        <ul className="doctor-emr-meta">
          <li>
            <span className="doctor-emr-meta__key">Запись</span>
            <span className="doctor-emr-meta__val">№ {data.patient.id}</span>
          </li>
          <li>
            <span className="doctor-emr-meta__key">Email</span>
            <span className="doctor-emr-meta__val">{data.patient.email}</span>
          </li>
          <li>
            <span className="doctor-emr-meta__key">Дата рождения</span>
            <span className="doctor-emr-meta__val">{prof.birth_date ? formatShortDate(prof.birth_date) : "—"}</span>
          </li>
          <li>
            <span className="doctor-emr-meta__key">Возраст</span>
            <span className="doctor-emr-meta__val">{ageStr}</span>
          </li>
        </ul>
        <div className="doctor-emr-clinical" role="group" aria-label="Клинические данные">
          <div className="doctor-emr-clinical__item">
            <span className="doctor-emr-clinical__label">Основной диагноз</span>
            <p className="doctor-emr-clinical__text">{prof.diagnosis?.trim() ? prof.diagnosis : "—"}</p>
          </div>
          <div className="doctor-emr-clinical__item">
            <span className="doctor-emr-clinical__label">Сопутствующие заболевания</span>
            <p className="doctor-emr-clinical__text">
              {prof.comorbidities?.trim() ? prof.comorbidities : "—"}
            </p>
          </div>
        </div>
      </header>

      {msg ? <StatusBanner variant="success">{msg}</StatusBanner> : null}

      <nav className="doctor-inline-nav doctor-inline-nav--tabs" aria-label="Разделы карточки">
        <a href="#doctor-section-card">1. Карта</a>
        <a href="#doctor-section-assign">2. Назначить</a>
        <a href="#doctor-section-stats">3. Статистика</a>
      </nav>

      <section className="settings-card doctor-panel ui-lift" id="doctor-section-card">
        <div className="section-head section-head--solo">
          <h2 className="section-title">Медицинская карта</h2>
        </div>
        <form className="doctor-card-form doctor-panel-body" onSubmit={saveProfile}>
          <div className="doctor-card-form__grid">
            <div className="field">
              <label className="form-label" htmlFor="full_name_official">
                ФИО полностью (как в документах)
              </label>
              <input
                className="form-control"
                id="full_name_official"
                value={fullNameOfficial}
                onChange={(e) => setFullNameOfficial(e.target.value)}
                placeholder={`Из учётной записи: ${data.patient.full_name}`}
                autoComplete="name"
              />
            </div>
            <div className="field">
              <label className="form-label" htmlFor="birth_date">
                Дата рождения
              </label>
              <input
                className="form-control"
                id="birth_date"
                type="date"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
              />
            </div>
          </div>
          <div className="field">
            <label className="form-label" htmlFor="diagnosis">
              Основной диагноз / заболевание
            </label>
            <textarea
              className="form-control"
              id="diagnosis"
              rows={3}
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              placeholder="Например: перелом, состояние после операции, ДДЗП…"
            />
          </div>
          <div className="field">
            <label className="form-label" htmlFor="comorbidities">
              Сопутствующие заболевания
            </label>
            <textarea
              className="form-control"
              id="comorbidities"
              rows={2}
              value={comorbidities}
              onChange={(e) => setComorbidities(e.target.value)}
              placeholder="Через запятую или списком"
            />
          </div>
          <div className="field">
            <label className="form-label" htmlFor="notes">
              Рекомендации для тренировки
            </label>
            <textarea className="form-control" id="notes" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="doctor-form-footer">
            <button className="btn btn-primary" type="submit">
              Сохранить карточку
            </button>
          </div>
        </form>
      </section>

      <section className="settings-card doctor-panel doctor-assign-panel ui-lift" id="doctor-section-assign">
        <div className="section-head section-head--solo">
          <h2 className="section-title">Назначить упражнения</h2>
        </div>

        <div className="doctor-panel-body doctor-assign-hub">
          {hasComplexes ? (
            <div className="doctor-assign-modes" role="tablist" aria-label="Способ назначения">
              <button
                type="button"
                role="tab"
                aria-selected={assignView === "complex"}
                className={`doctor-assign-mode${assignView === "complex" ? " is-active" : ""}`}
                onClick={() => setAssignMode("complex")}
              >
                <span className="doctor-assign-mode__title">Комплекс</span>
                <span className="doctor-assign-mode__sub">Готовый набор сразу</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={assignView === "single"}
                className={`doctor-assign-mode${assignView === "single" ? " is-active" : ""}`}
                onClick={() => setAssignMode("single")}
              >
                <span className="doctor-assign-mode__title">Одно упражнение</span>
                <span className="doctor-assign-mode__sub">Точечно, с параметрами</span>
              </button>
            </div>
          ) : null}

          {assignView === "complex" ? (
            <div className="doctor-assign-pane" role="tabpanel">
              <p className="doctor-assign-pane__lead">
                Выберите комплекс — в кабинет пациента попадут все перечисленные упражнения с указанным числом повторов.
              </p>
              <div className="doctor-complex-grid">
                {assignmentComplexes.map((c) => {
                  const shortLabel = c.label.replace(/^Комплекс:\s*/i, "");
                  const selected = complexId === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      className={`doctor-complex-card${selected ? " is-selected" : ""}`}
                      aria-pressed={selected}
                      onClick={() => setComplexId(c.id)}
                    >
                      <div className="doctor-complex-card__head">
                        <span className="doctor-complex-card__title">{shortLabel}</span>
                        <span className="doctor-complex-card__badge">
                          {c.exercise_count}{" "}
                          {c.exercise_count === 1 ? "упражнение" : "упражнения"}
                        </span>
                      </div>
                      {c.description ? (
                        <p className="doctor-complex-card__desc">{c.description}</p>
                      ) : null}
                      <p className="doctor-complex-card__compose-label">Состав комплекса</p>
                      <ol className="doctor-complex-card__compose" aria-label="Упражнения в комплексе">
                        {c.items.map((it, idx) => {
                          const sideHint = complexComposeSideHint(it);
                          return (
                            <li key={it.exercise_key} className="doctor-complex-card__compose-row">
                              <span className="doctor-complex-card__compose-num">{idx + 1}</span>
                              <span className="doctor-complex-card__compose-name">
                                {it.exercise_label}
                                {sideHint ? (
                                  <span className="doctor-complex-card__compose-side-tag">{sideHint}</span>
                                ) : null}
                              </span>
                              <span className="doctor-complex-card__compose-meta">{it.detail}</span>
                            </li>
                          );
                        })}
                      </ol>
                    </button>
                  );
                })}
              </div>


              <div className="doctor-assign-pane__actions">
                <button
                  type="button"
                  className="btn btn-primary btn-lg"
                  disabled={!complexId || complexBusy}
                  onClick={assignComplex}
                >
                  {complexBusy ? "Назначаем…" : "Назначить комплекс"}
                </button>
              </div>
            </div>
          ) : (
            <form className="doctor-assign-pane doctor-assign-pane--single" onSubmit={assign}>
              <p className="doctor-assign-pane__lead">
                Выберите упражнение и параметры — в кабинет пациента добавится одна запись.
              </p>

              <div className="doctor-single-grid">
                <div className="field doctor-single-grid__exercise">
                  <label className="form-label" htmlFor="exercise_id">
                    Упражнение
                  </label>
                  <select
                    className="form-control"
                    id="exercise_id"
                    required
                    value={exerciseId}
                    onChange={(e) => {
                      const v = e.target.value;
                      setExerciseId(v);
                      const ex = doctorExercises.find((x) => String(x.id) === v);
                      if (ex?.default_reps != null) setTargetReps(ex.default_reps);
                    }}
                  >
                    {exercisesByGroup
                      ? exercisesByGroup.map((g) => (
                          <optgroup key={g.id} label={g.label}>
                            {g.exercises.map((ex) => (
                              <option key={ex.id} value={String(ex.id)}>
                                {ex.label}
                              </option>
                            ))}
                          </optgroup>
                        ))
                      : doctorExercises.map((ex) => (
                          <option key={ex.id} value={String(ex.id)}>
                            {ex.label}
                          </option>
                        ))}
                  </select>
                </div>

                <div className="doctor-single-toolbar">
                  <div className="doctor-single-params">
                  <div className="field doctor-single-grid__reps">
                    <label className="form-label" htmlFor="target_reps">
                      Повторов
                    </label>
                    <input
                      className="form-control"
                      id="target_reps"
                      type="number"
                      min={1}
                      max={50}
                      value={targetReps}
                      onChange={(e) => setTargetReps(e.target.value)}
                    />
                  </div>

                    {showSideField ? (
                      <div className="field doctor-single-grid__side">
                        <label className="form-label" htmlFor="side">
                          Сторона
                        </label>
                        <select
                          className="form-control"
                          id="side"
                          value={side}
                          onChange={(e) => setSide(e.target.value)}
                        >
                          <option value="left">Левая</option>
                          <option value="right">Правая</option>
                        </select>
                      </div>
                    ) : null}

                    {!isDualArm ? (
                      <div className="doctor-single-grid__both">
                        <label className="check-label doctor-single-both">
                          <input type="checkbox" checked={bothArms} onChange={(e) => setBothArms(e.target.checked)} />
                          <span>{bothSidesAssignLabel(selectedEx?.key)}</span>
                        </label>
                      </div>
                    ) : null}
                  </div>

                  <div className="field doctor-single-grid__actions">
                    <span className="form-label doctor-single-grid__actions-label" aria-hidden="true">
                      &nbsp;
                    </span>
                    <button className="btn btn-primary btn-lg" type="submit">
                      Добавить упражнение
                    </button>
                  </div>
                </div>
              </div>
            </form>
          )}

          <div className="doctor-assign-active" id="doctor-section-active">
            <h3 className="doctor-assign-active__title">Что пациенту нужно выполнить</h3>
            {data.assignment_display?.length ? (
              <ul className="assignments-list assignments-list--doctor">
                {data.assignment_display.map((row, idx) => (
                  <li className="assignment-row assignment-row--doctor" key={idx}>
                    <div className="assignment-row__copy">
                      <strong>{row.exercise_label}</strong>
                      <span>{row.detail}</span>
                      <span className="muted">от {formatShortDate(row.created_at)}</span>
                    </div>
                    <button type="button" className="btn btn-danger btn-sm" onClick={() => deactivate(row)}>
                      Снять
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="body-text muted">Пока ничего не назначено.</p>
            )}
          </div>
        </div>
      </section>

      <TrainingStats
        variant="doctor"
        sectionClassName="doctor-panel"
        sectionId="doctor-section-stats"
        statsRows={data.stats_rows}
        statsSummary={data.stats_summary}
        statsChart={data.stats_chart}
        statsExerciseChart={data.stats_exercise_chart}
        lastSession={data.last_session}
      />
    </div>
  );
}
