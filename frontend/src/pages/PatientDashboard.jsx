import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useSession } from "../hooks/SessionContext.jsx";
import TrainingStats from "../components/TrainingStats.jsx";
import { EmptyState, PageError, PageHeader, PageLoading } from "../components/ui/PagePrimitives.jsx";
import { greetingNameFromFio } from "../utils/greetingName.js";
import { formatRelativeDayRu, parseUtcIso } from "../utils/dateTime.js";

function formatRelativeSession(iso) {
  return formatRelativeDayRu(iso);
}

function assignWord(n) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return "назначение";
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return "назначения";
  return "назначений";
}

function formatShortDate(iso) {
  const d = parseUtcIso(iso);
  if (!d) return "—";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

export default function PatientDashboard() {
  const { user, loading: sessionLoading } = useSession();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setErr(null);
    fetch("/api/patient/dashboard", { credentials: "same-origin" })
      .then(async (r) => {
        if (r.status === 403) return null;
        if (!r.ok) throw new Error("bad");
        return r.json();
      })
      .then((j) => {
        if (!j) setErr("forbidden");
        else setData(j);
      })
      .catch(() => setErr("bad"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const lastSessionRel = useMemo(() => formatRelativeSession(data?.last_session?.completed_at), [data?.last_session?.completed_at]);

  if (sessionLoading) {
    return (
      <div className="page-shell">
        <PageLoading />
      </div>
    );
  }

  if (user?.role && user.role !== "patient") {
    return <Navigate to="/doctor/" replace />;
  }

  if (err === "forbidden") {
    return <Navigate to="/doctor/" replace />;
  }

  if (err === "bad") {
    return (
      <div className="page-shell">
        <PageError message="Проверьте подключение и обновите страницу." onRetry={load} />
      </div>
    );
  }

  if (!data?.ok) {
    return (
      <div className="page-shell">
        <PageLoading label="Загрузка кабинета…" />
      </div>
    );
  }

  const { profile, todo_plan, last_session, stats_rows, stats_summary, stats_chart, stats_exercise_chart } =
    data;
  const plan = todo_plan?.length ? todo_plan : [];
  const nAssign = plan.length;
  const primaryToRehab = nAssign ? `/patient/rehab/?a=${plan[0].primary_id}` : "/patient/rehab/";
  const fullName = profile?.full_name_display?.trim() || user?.full_name || "";
  const greetingName = greetingNameFromFio(fullName) || "пациент";

  const subtitleParts = [];
  if (nAssign) subtitleParts.push(`${nAssign} ${assignWord(nAssign)} от врача`);
  if (last_session && lastSessionRel) subtitleParts.push(`последняя тренировка ${lastSessionRel}`);

  return (
    <div className="page-shell patient-dashboard">
      <PageHeader
        kicker="Кабинет пациента"
        title={`Здравствуйте, ${greetingName}`}
        subtitle={subtitleParts.length ? subtitleParts.join(" · ") : "Врач пока не назначил упражнения"}
        actions={
          <Link className="btn btn-primary btn-lg" to={primaryToRehab}>
            {nAssign ? "К тренировке" : "Раздел тренировки"}
          </Link>
        }
      />

      <nav className="patient-inline-nav" aria-label="Разделы кабинета">
        <a href="#patient-assignments">Назначения</a>
        <Link to="/patient/stats">Статистика</Link>
        <a href="#patient-profile">От врача</a>
      </nav>

      <section className="settings-card ui-lift patient-dashboard-assignments" id="patient-assignments">
        <div className="section-head">
          <div>
            <h2 className="section-title">Что нужно выполнить</h2>
            <p className="section-desc muted">
              Назначено врачом — выполняйте по списку. Для каждого пункта откройте тренировку с камерой.
            </p>
          </div>
        </div>
        {plan.length ? (
          <ol className="patient-todo-plan">
            {plan.map((row, idx) => (
              <li key={row.primary_id || row.ids?.join("-")} className="patient-todo-plan__item">
                <span className="patient-todo-plan__num" aria-hidden="true">
                  {idx + 1}
                </span>
                <div className="patient-todo-plan__body">
                  <strong className="patient-todo-plan__title">{row.exercise_label}</strong>
                  <span className="patient-todo-plan__detail">{row.detail}</span>
                </div>
                <Link className="btn btn-primary btn-sm" to={`/patient/rehab/?a=${row.primary_id}`}>
                  Выполнить
                </Link>
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState
            title="Пока ничего не назначено"
            description="Когда врач добавит упражнения, здесь появится список того, что нужно выполнить."
          />
        )}
      </section>

      <div id="patient-stats">
        <TrainingStats
          variant="patient"
          sectionClassName="patient-stats-panel"
          statsRows={stats_rows}
          statsSummary={stats_summary}
          statsChart={stats_chart}
          statsExerciseChart={stats_exercise_chart}
          lastSession={last_session}
        />
      </div>

      <div className="patient-dashboard-columns">
        <aside
          id="patient-profile"
          className="instruction-card ui-lift patient-dashboard-profile patient-readonly-panel"
          aria-label="Данные от врача"
        >
          <div className="section-head section-head--solo">
            <h2 className="section-title">От врача</h2>
          </div>
          <div className="kv-grid kv-grid--tight">
            <div>
              <span className="mini-label">ФИО</span>
              <p className="body-text">{profile?.full_name_display?.trim() || user?.full_name || "—"}</p>
            </div>
            <div>
              <span className="mini-label">Дата рождения</span>
              <p className="body-text">
                {profile?.birth_date ? formatShortDate(profile.birth_date) : "—"}
                {profile?.age_years != null ? ` · ${profile.age_years} лет` : ""}
              </p>
            </div>
            <div>
              <span className="mini-label">Диагноз</span>
              <p className="body-text">{profile?.diagnosis || "—"}</p>
            </div>
            <div>
              <span className="mini-label">Сопутствующие</span>
              <p className="body-text">{profile?.comorbidities?.trim() ? profile.comorbidities : "—"}</p>
            </div>
            <div className="kv-grid__full">
              <span className="mini-label">Рекомендации</span>
              <p className="body-text">{profile?.notes || "—"}</p>
            </div>
          </div>
          {last_session ? (
            <div className="patient-last-session">
              <Link className="text-link" to="/patient/stats">
                Статистика выполнения →
              </Link>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
