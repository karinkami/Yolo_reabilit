import { NavLink, Outlet, Navigate, useLocation } from "react-router-dom";
import { useSession } from "../hooks/SessionContext.jsx";

function userDisplayName(user) {
  const name = (user?.full_name || "").trim();
  if (name) return name;
  return user?.email || (user?.role === "doctor" ? "Врач" : "Пациент");
}

function NavItem({ to, end, children }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) => `shell-nav-link${isActive ? " nav-active" : ""}`}
    >
      {children}
    </NavLink>
  );
}

export default function ProtectedLayout() {
  const { user, loading } = useSession();
  const location = useLocation();

  if (loading) {
    return (
      <div className="shell-loading">
        <span className="page-state__spinner" aria-hidden />
        <p className="body-text muted">Загрузка…</p>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/auth/login" replace />;
  }

  const home = user.role === "doctor" ? "/doctor/" : "/patient/";
  const display = userDisplayName(user);
  const onPatientCard = user.role === "doctor" && /^\/doctor\/patient\/\d+/.test(location.pathname);

  return (
    <div className="app-root-react">
      <header className="shell-nav" aria-label="Главное меню">
        <div className="shell-nav-inner">
          <div className="shell-nav-start">
            <NavLink to={home} className="shell-brand" end>
              <span className="shell-brand-mark" aria-hidden />
              <span className="shell-brand-text">
                <span className="shell-brand-name">Reabilit</span>
                <span className="shell-brand-tag">реабилитация</span>
              </span>
            </NavLink>
          </div>

          <nav className="shell-nav-body" aria-label="Разделы">
            {user.role === "patient" ? (
              <div className="shell-nav-links">
                <NavItem to="/patient/" end>
                  Кабинет
                </NavItem>
                <NavItem to="/patient/rehab/">Тренировка</NavItem>
                <NavItem to="/patient/stats">Статистика</NavItem>
              </div>
            ) : (
              <div className="shell-nav-links">
                <NavItem to="/doctor/" end>
                  Пациенты
                </NavItem>
                {onPatientCard ? (
                  <span className="shell-nav-context muted">Карточка пациента</span>
                ) : null}
              </div>
            )}
          </nav>

          <div className="shell-nav-end">
            <span className="shell-nav-user" title={user.email || display}>
              <span className="shell-nav-user__name">{display}</span>
            </span>
            <a className="shell-nav-logout" href="/auth/logout">
              Выйти
            </a>
          </div>
        </div>
      </header>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
