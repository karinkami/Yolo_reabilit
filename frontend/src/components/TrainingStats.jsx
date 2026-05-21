import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";
import { formatDateTimeLocal } from "../utils/dateTime.js";

const CHART_PALETTE = [
  "rgba(90, 140, 134, 0.75)",
  "rgba(110, 118, 160, 0.72)",
  "rgba(143, 168, 130, 0.78)",
  "rgba(91, 126, 154, 0.72)",
  "rgba(160, 140, 120, 0.72)",
  "rgba(120, 150, 170, 0.72)",
  "rgba(100, 130, 110, 0.72)",
  "rgba(150, 120, 140, 0.72)",
];

export default function TrainingStats({
  statsRows = [],
  statsSummary = {},
  statsChart = null,
  statsExerciseChart = null,
  lastSession = null,
  sectionId,
  sectionClassName = "",
  variant = "default",
}) {
  const activityCanvasRef = useRef(null);
  const exerciseCanvasRef = useRef(null);
  const activityChartRef = useRef(null);
  const exerciseChartRef = useRef(null);

  const isDoctor = variant === "doctor";
  const isPatient = variant === "patient";
  const hasAnyData = Boolean(statsSummary?.total_sessions || statsRows?.length);

  useEffect(() => {
    const canvas = activityCanvasRef.current;
    if (!canvas || !statsChart?.labels?.length) return;
    const ctx = canvas.getContext("2d");
    if (activityChartRef.current) activityChartRef.current.destroy();
    activityChartRef.current = new Chart(ctx, {
      data: {
        labels: statsChart.labels,
        datasets: [
          {
            type: "bar",
            label: "Подходов за день",
            data: statsChart.session_counts,
            yAxisID: "y",
            backgroundColor: "rgba(90, 140, 134, 0.38)",
            borderColor: "rgba(90, 140, 134, 0.55)",
            borderWidth: 1,
            borderRadius: 6,
          },
          {
            type: "line",
            label: "Средняя оценка %",
            data: statsChart.avg_scores,
            yAxisID: "y1",
            tension: 0.35,
            borderColor: "rgba(110, 118, 160, 0.7)",
            backgroundColor: "rgba(110, 118, 160, 0.08)",
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 5,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom" },
          tooltip: { enabled: true },
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Подходы" },
            ticks: { stepSize: 1, precision: 0 },
            beginAtZero: true,
          },
          y1: {
            type: "linear",
            position: "right",
            title: { display: true, text: "%" },
            grid: { drawOnChartArea: false },
            min: 0,
            max: 100,
          },
        },
      },
    });
    return () => {
      if (activityChartRef.current) {
        activityChartRef.current.destroy();
        activityChartRef.current = null;
      }
    };
  }, [statsChart]);

  useEffect(() => {
    const canvas = exerciseCanvasRef.current;
    if (!canvas || !statsExerciseChart?.labels?.length) return;
    const ctx = canvas.getContext("2d");
    if (exerciseChartRef.current) exerciseChartRef.current.destroy();
    exerciseChartRef.current = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: statsExerciseChart.labels,
        datasets: [
          {
            data: statsExerciseChart.session_counts,
            backgroundColor: CHART_PALETTE.slice(0, statsExerciseChart.labels.length),
            borderWidth: 2,
            borderColor: "#fafbfc",
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: { enabled: true },
        },
      },
    });
    return () => {
      if (exerciseChartRef.current) {
        exerciseChartRef.current.destroy();
        exerciseChartRef.current = null;
      }
    };
  }, [statsExerciseChart]);

  const metrics = [
    { label: "Подходов всего", value: statsSummary?.total_sessions ?? 0 },
    { label: "Упражнений", value: statsSummary?.exercise_kinds ?? 0 },
    { label: "Средняя оценка", value: statsSummary?.avg_score != null ? `${statsSummary.avg_score}%` : "—" },
    { label: "За 7 дней", value: statsSummary?.sessions_last_7_days ?? 0 },
    {
      label: "Активных дней",
      value: statsSummary?.active_days_last_14 != null ? `${statsSummary.active_days_last_14} / 14` : "—",
    },
  ];

  if (statsSummary?.best_score != null) {
    metrics.push({ label: "Лучшая оценка", value: `${statsSummary.best_score}%` });
  }

  return (
    <section
      className={["settings-card", "stats-card", "ui-lift", sectionClassName].filter(Boolean).join(" ")}
      id={sectionId || undefined}
    >
      <div className="section-head section-head--solo stats-section-head">
        <div>
          <h2 className="section-title">Статистика тренировок</h2>
          {isDoctor ? (
            <p className="section-desc muted stats-card__intro">
              Динамика подходов, оценка качества и разбивка по упражнениям за последние две недели.
            </p>
          ) : isPatient ? (
            <p className="section-desc muted stats-card__intro">
              Ваш прогресс: сколько подходов выполнено, средняя оценка и разбивка по упражнениям за 14 дней.
            </p>
          ) : (
            <p className="section-desc muted stats-card__intro">
              Подходы, оценки и графики по завершённым тренировкам.
            </p>
          )}
        </div>
      </div>

      {hasAnyData ? (
        <>
          <div className="metric-row stats-metric-row" role="list">
            {metrics.map((m) => (
              <div className="metric-tile stats-metric-tile" role="listitem" key={m.label}>
                <span className="metric-tile__label">{m.label}</span>
                <strong className="metric-tile__value">{m.value}</strong>
              </div>
            ))}
          </div>

          {lastSession ? (
            <div className="stats-last-session ui-lift">
              <span className="stats-last-session__label">Последний подход</span>
              <p className="stats-last-session__text">
                <strong>{lastSession.exercise_label}</strong>
                {" · "}
                {lastSession.reps_completed}/{lastSession.target_reps} повт.
                {" · "}
                <span className="stats-last-session__score">{lastSession.score_percent}%</span>
                {" · "}
                <span className="muted">{formatDateTimeLocal(lastSession.completed_at)}</span>
              </p>
            </div>
          ) : null}

          <div className="stats-charts-grid">
            {statsChart?.labels?.length ? (
              <div className="stats-chart-block">
                <h3 className="stats-chart-title">Активность за {statsChart.days} дней</h3>
                <p className="stats-chart-legend muted">Столбцы — число подходов, линия — средняя оценка качества (%)</p>
                <div className="stats-chart-canvas-wrap">
                  <canvas ref={activityCanvasRef} aria-label="График активности по дням" />
                </div>
              </div>
            ) : null}

            {statsExerciseChart?.labels?.length ? (
              <div className="stats-chart-block stats-chart-block--donut">
                <h3 className="stats-chart-title">Подходы по упражнениям</h3>
                <p className="stats-chart-legend muted">Доля завершённых подходов по каждому упражнению</p>
                <div className="stats-chart-canvas-wrap stats-chart-canvas-wrap--donut">
                  <canvas ref={exerciseCanvasRef} aria-label="Распределение подходов по упражнениям" />
                </div>
              </div>
            ) : null}
          </div>

          {statsRows?.length ? (
            <div className="table-wrap stats-table-wrap">
              <h3 className="stats-table-heading">Детализация по упражнениям</h3>
              <table className="data-table stats-table">
                <thead>
                  <tr>
                    <th>Упражнение</th>
                    <th>Подходов</th>
                    <th>Повторов</th>
                    <th>Оценка</th>
                    <th>Статус</th>
                    <th>Последний раз</th>
                  </tr>
                </thead>
                <tbody>
                  {statsRows.map((r) => (
                    <tr
                      key={r.exercise_key + String(r.label)}
                      className={r.is_incomplete_bundle ? "history-row--half-bundle" : undefined}
                    >
                      <td>
                        <span className="history-exercise-cell">
                          <span>{r.label}</span>
                          {r.bundle_progress_label ? (
                            <span
                              className={
                                r.is_incomplete_bundle
                                  ? "history-bundle-badge history-bundle-badge--half"
                                  : "history-bundle-badge history-bundle-badge--done"
                              }
                            >
                              {r.bundle_progress_label}
                            </span>
                          ) : null}
                        </span>
                      </td>
                      <td>{r.sessions}</td>
                      <td>{r.total_reps}</td>
                      <td className={r.is_incomplete_bundle ? "history-score--half" : undefined}>
                        <div className="stats-score-cell">
                          <div
                            className="stats-score-bar"
                            role="presentation"
                            style={{ width: `${Math.min(100, Math.max(0, r.avg_score))}%` }}
                          />
                          <span className="stats-score-value">{r.avg_score}%</span>
                        </div>
                      </td>
                      <td>{r.status_label || "—"}</td>
                      <td className="stats-table-date">{formatDateTimeLocal(r.last_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      ) : (
        <p className="body-text muted stats-empty">Нет данных по завершённым подходам. После первых тренировок здесь появятся графики и прогресс.</p>
      )}
    </section>
  );
}
