import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import TrainingStats from "../components/TrainingStats.jsx";
import { useSession } from "../hooks/SessionContext.jsx";
import { PageError, PageHeader, PageLoading } from "../components/ui/PagePrimitives.jsx";

export default function PatientStats() {
  const { user, loading: sessionLoading } = useSession();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setErr(null);
    fetch("/api/patient/stats", { credentials: "same-origin" })
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
        <PageLoading label="Загрузка статистики…" />
      </div>
    );
  }

  return (
    <div className="page-shell patient-stats-page">
      <PageHeader
        kicker="Пациент"
        title="Статистика выполнения"
        subtitle="Подходы, оценки и детализация по упражнениям"
        back={{ to: "/patient/", label: "Кабинет" }}
      />
      <TrainingStats
        variant="patient"
        sectionClassName="patient-stats-panel"
        statsRows={data.stats_rows}
        statsSummary={data.stats_summary}
        statsChart={data.stats_chart}
        statsExerciseChart={data.stats_exercise_chart}
        lastSession={data.last_session}
      />
    </div>
  );
}
