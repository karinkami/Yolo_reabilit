import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useSession } from "../hooks/SessionContext.jsx";
import { PageHeader, PageLoading, StatusBanner } from "../components/ui/PagePrimitives.jsx";
import { formatRelativeDayRu, parseUtcIso } from "../utils/dateTime.js";

function formatLastActive(iso) {
  if (!iso) return "не было подходов";
  return formatRelativeDayRu(iso) || "—";
}

export default function DoctorDashboard() {
  const { user, loading: sessionLoading } = useSession();
  const [rawPatients, setRawPatients] = useState(null);
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [createEmail, setCreateEmail] = useState("");
  const [createName, setCreateName] = useState("");
  const [createBusy, setCreateBusy] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const loadPatients = useCallback(() => {
    return fetch("/api/doctor/patients", { credentials: "same-origin" })
      .then((r) => r.json())
      .then((d) => setRawPatients(d.patients || []))
      .catch(() => setRawPatients([]));
  }, []);

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  const patients = useMemo(() => {
    if (!rawPatients?.length) return [];
    const q = query.trim().toLowerCase();
    let list = q
      ? rawPatients.filter(
          (p) =>
            (p.full_name || "").toLowerCase().includes(q) || (p.email || "").toLowerCase().includes(q)
        )
      : [...rawPatients];
    if (sortBy === "name") {
      list.sort((a, b) => (a.full_name || "").localeCompare(b.full_name || "", "ru"));
    } else {
      list.sort((a, b) => {
        const ta = a.last_session_at ? (parseUtcIso(a.last_session_at)?.getTime() ?? 0) : 0;
        const tb = b.last_session_at ? (parseUtcIso(b.last_session_at)?.getTime() ?? 0) : 0;
        return tb - ta;
      });
    }
    return list;
  }, [rawPatients, query, sortBy]);

  const pendingCount = useMemo(
    () => (rawPatients || []).filter((p) => p.registration_pending).length,
    [rawPatients]
  );

  const submitCreate = async (e) => {
    e.preventDefault();
    setCreateBusy(true);
    setErr("");
    setMsg("");
    const res = await fetch("/api/doctor/patients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ email: createEmail.trim(), full_name: createName.trim() }),
    });
    const data = await res.json().catch(() => ({}));
    setCreateBusy(false);
    if (!res.ok) {
      setErr(data.error || "Не удалось создать пациента");
      return;
    }
    setMsg(data.message || "Пациент создан.");
    setCreateOpen(false);
    setCreateEmail("");
    setCreateName("");
    await loadPatients();
  };

  const deletePatient = async (p) => {
    const label = p.full_name || p.email;
    if (
      !window.confirm(
        `Удалить пациента «${label}»?\n\nБудут удалены карточка, назначения и история тренировок. Это действие нельзя отменить.`
      )
    ) {
      return;
    }
    setDeletingId(p.id);
    setErr("");
    setMsg("");
    const res = await fetch(`/api/doctor/patient/${p.id}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    setDeletingId(null);
    if (!res.ok) {
      setErr(data.error || "Не удалось удалить");
      return;
    }
    setMsg(`Пациент «${label}» удалён.`);
    await loadPatients();
  };

  if (sessionLoading) {
    return (
      <div className="page-shell doctor-dashboard-page">
        <PageLoading />
      </div>
    );
  }

  if (user?.role && user.role !== "doctor") {
    return <Navigate to="/patient/" replace />;
  }

  if (rawPatients === null) {
    return (
      <div className="page-shell doctor-dashboard-page">
        <PageLoading label="Загрузка списка…" />
      </div>
    );
  }

  const summaryParts = [`Всего ${rawPatients.length}`];
  if (pendingCount) summaryParts.push(`ожидают регистрации: ${pendingCount}`);
  if (query) summaryParts.push(`найдено: ${patients.length}`);

  return (
    <div className="page-shell doctor-dashboard-page">
      <PageHeader
        kicker="Кабинет врача"
        title="Пациенты"
        subtitle={summaryParts.join(" · ")}
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            Новый пациент
          </button>
        }
      />

      {msg ? <StatusBanner variant="success">{msg}</StatusBanner> : null}
      {err ? <StatusBanner variant="error">{err}</StatusBanner> : null}

      <div className="doctor-toolbar doctor-toolbar--wide ui-lift">
        <label className="doctor-search-label">
          <span className="form-label">Поиск</span>
          <input
            className="form-control doctor-search-input"
            type="search"
            placeholder="Имя или email…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
        </label>
        <div className="doctor-sort">
          <span className="form-label doctor-sort-label">Сортировка</span>
          <select
            className="form-control doctor-sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            aria-label="Сортировка списка"
          >
            <option value="name">По имени</option>
            <option value="activity">По последней тренировке</option>
          </select>
        </div>
      </div>

      <section className="doctor-patient-table-card ui-lift">
        {patients.length ? (
          <div className="doctor-patient-table-wrap">
            <table className="doctor-patient-table">
              <thead>
                <tr>
                  <th>Пациент</th>
                  <th>Статус</th>
                  <th>Назначения</th>
                  <th>Активность</th>
                  <th aria-label="Действия" />
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <tr key={p.id}>
                    <td className="doctor-patient-table__identity">
                      <strong>{p.full_name}</strong>
                      <span className="muted">{p.email}</span>
                    </td>
                    <td>
                      {p.registration_pending ? (
                        <span className="patient-badge patient-badge--pending">Ожидает регистрации</span>
                      ) : (
                        <span className="patient-badge patient-badge--ok">В системе</span>
                      )}
                    </td>
                    <td>
                      <span
                        className={
                          p.active_assignments_count ? "patient-badge patient-badge--ok" : "patient-badge"
                        }
                      >
                        {p.active_assignments_count
                          ? `${p.active_assignments_count} активн.`
                          : "нет назначений"}
                      </span>
                    </td>
                    <td className="muted doctor-patient-table__activity">{formatLastActive(p.last_session_at)}</td>
                    <td className="doctor-patient-table__actions">
                      <Link className="btn btn-primary btn-sm" to={`/doctor/patient/${p.id}`}>
                        Карточка
                      </Link>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        disabled={deletingId === p.id}
                        onClick={() => deletePatient(p)}
                      >
                        {deletingId === p.id ? "…" : "Удалить"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : rawPatients.length === 0 ? (
          <div className="doctor-empty-state">
            <p className="body-text">Пока нет пациентов.</p>
            <p className="body-text muted">
              Создайте карточку кнопкой «Новый пациент» — пациент зарегистрируется с тем же email и задаст пароль.
            </p>
            <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
              Создать первого пациента
            </button>
          </div>
        ) : (
          <p className="body-text muted">Никого не найдено — измените запрос.</p>
        )}
      </section>

      {createOpen ? (
        <div className="doctor-modal-backdrop" role="presentation" onClick={() => !createBusy && setCreateOpen(false)}>
          <div
            className="doctor-modal ui-lift"
            role="dialog"
            aria-labelledby="create-patient-title"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="doctor-modal__head">
              <h2 id="create-patient-title" className="section-title">
                Новый пациент
              </h2>
              <button
                type="button"
                className="doctor-modal__close"
                aria-label="Закрыть"
                disabled={createBusy}
                onClick={() => setCreateOpen(false)}
              >
                ×
              </button>
            </div>
            <p className="body-text muted doctor-modal__lead">
              Укажите email и ФИО. Пациент откроет страницу «Регистрация», введёт <strong>тот же email</strong> и
              придумает пароль — после этого сможет войти и видеть ваши назначения.
            </p>
            <form className="doctor-modal__form" onSubmit={submitCreate}>
              <div className="field">
                <label className="form-label" htmlFor="create_full_name">
                  ФИО
                </label>
                <input
                  className="form-control"
                  id="create_full_name"
                  required
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="Иванов Иван Иванович"
                  autoComplete="name"
                />
              </div>
              <div className="field">
                <label className="form-label" htmlFor="create_email">
                  Email (для регистрации пациента)
                </label>
                <input
                  className="form-control"
                  id="create_email"
                  type="email"
                  required
                  value={createEmail}
                  onChange={(e) => setCreateEmail(e.target.value)}
                  placeholder="patient@example.com"
                  autoComplete="off"
                />
              </div>
              <div className="doctor-modal__footer">
                <button type="button" className="btn btn-secondary" disabled={createBusy} onClick={() => setCreateOpen(false)}>
                  Отмена
                </button>
                <button type="submit" className="btn btn-primary" disabled={createBusy}>
                  {createBusy ? "Сохранение…" : "Создать"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
