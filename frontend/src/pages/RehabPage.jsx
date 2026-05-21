import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import RehabTraining from "../RehabTraining.jsx";
import { PageError, PageHeader, PageLoading } from "../components/ui/PagePrimitives.jsx";

export default function RehabPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialAssignmentId = useMemo(() => {
    const raw = searchParams.get("a");
    if (!raw || !/^\d+$/.test(raw)) return null;
    return Number.parseInt(raw, 10);
  }, [searchParams]);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setErr(null);
    fetch("/patient/rehab/api/bootstrap", { credentials: "same-origin" })
      .then(async (r) => {
        if (r.status === 401) {
          navigate("/auth/login", { replace: true });
          return null;
        }
        if (!r.ok) throw new Error("load");
        return r.json();
      })
      .then((j) => {
        if (j) setData(j);
      })
      .catch(() => setErr("load"));
  }, [navigate]);

  useEffect(() => {
    load();
  }, [load]);

  if (err) {
    return (
      <div className="page-shell">
        <PageHeader title="Тренировка" back={{ to: "/patient/", label: "Кабинет" }} />
        <PageError message="Не удалось загрузить данные. Попробуйте ещё раз." onRetry={load} />
      </div>
    );
  }
  if (!data?.ok) {
    return (
      <div className="page-shell">
        <PageLoading label="Подготовка тренировки…" />
      </div>
    );
  }

  return (
    <div className="page-shell rehab-page-shell">
      <PageHeader
        kicker="Пациент"
        title="Тренировка"
        subtitle={data.hasAssignments ? "Слева камера, справа подсказки по ходу" : "Нет назначений от врача"}
        back={{ to: "/patient/", label: "Кабинет" }}
      />
      <RehabTraining
        embedded
        initialAssignmentId={initialAssignmentId}
        urls={data.urls}
        bootstrap={{
          hasAssignments: data.hasAssignments,
          options: data.options,
          personalRecommendations: data.personalRecommendations || "",
        }}
      />
    </div>
  );
}
