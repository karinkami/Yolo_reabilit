import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSession } from "../hooks/SessionContext.jsx";

export default function LoginPage() {
  const navigate = useNavigate();
  const { user, loading, reload } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [flashMsg, setFlashMsg] = useState("");

  useEffect(() => {
    fetch("/api/flash", { credentials: "same-origin" })
      .then((r) => r.json())
      .then((d) => {
        const items = d.items || [];
        if (items.length) {
          setFlashMsg(items.map((x) => x.message).join(" "));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (loading) return;
    if (user) {
      navigate(user.role === "doctor" ? "/doctor/" : "/patient/", { replace: true });
    }
  }, [user, loading, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || "Ошибка входа");
      return;
    }
    await reload();
    navigate(data.user?.role === "doctor" ? "/doctor/" : "/patient/", { replace: true });
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
        <h1 className="auth-title">Вход</h1>
        {(error || flashMsg) && <p className="auth-alert">{error || flashMsg}</p>}
        <form className="auth-form" onSubmit={submit}>
          <label className="form-label" htmlFor="email">
            Email
          </label>
          <input
            className="form-control"
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <label className="form-label" htmlFor="password">
            Пароль
          </label>
          <input
            className="form-control"
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button className="btn btn-primary btn-block" type="submit">
            Войти
          </button>
        </form>
        <p className="auth-footer">
          Нет аккаунта пациента? <Link to="/auth/register">Регистрация</Link>
        </p>
      </div>
    </div>
  );
}
