import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSession } from "../hooks/SessionContext.jsx";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { user, loading, reload } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading) return;
    if (user) navigate("/patient/", { replace: true });
  }, [user, loading, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || "Ошибка регистрации");
      return;
    }
    await reload();
    navigate("/patient/", { replace: true });
  };

  if (loading || user) {
    return (
      <div className="auth-shell">
        <p className="body-text muted">Загрузка…</p>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1 className="auth-title">Регистрация</h1>
        <p className="auth-hint muted">
          Если врач уже создал для вас карточку, укажите <strong>тот же email</strong> и задайте пароль — вход
          откроется автоматически.
        </p>
        {error && <p className="auth-alert">{error}</p>}
        <form className="auth-form" onSubmit={submit}>
          <label className="form-label" htmlFor="full_name">
            ФИО
          </label>
          <input
            className="form-control"
            id="full_name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <label className="form-label" htmlFor="email">
            Email
          </label>
          <input
            className="form-control"
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <label className="form-label" htmlFor="password">
            Пароль (не короче 6 символов)
          </label>
          <input
            className="form-control"
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button className="btn btn-primary btn-block" type="submit">
            Зарегистрироваться
          </button>
        </form>
        <p className="auth-footer">
          Уже есть аккаунт? <Link to="/auth/login">Вход</Link>
        </p>
      </div>
    </div>
  );
}
