import { Link } from "react-router-dom";

export function PageLoading({ label = "Загрузка…" }) {
  return (
    <div className="page-state page-state--loading" role="status">
      <span className="page-state__spinner" aria-hidden />
      <p className="body-text muted">{label}</p>
    </div>
  );
}

export function PageError({ title = "Не удалось загрузить", message, onRetry }) {
  return (
    <div className="page-state page-state--error" role="alert">
      <p className="page-state__title">{title}</p>
      {message ? <p className="body-text muted">{message}</p> : null}
      {onRetry ? (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Повторить
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="empty-state">
      <p className="empty-state__title">{title}</p>
      {description ? <p className="empty-state__desc muted">{description}</p> : null}
      {action ?? null}
    </div>
  );
}

export function StatusBanner({ children, variant = "info" }) {
  return (
    <div className={`ui-banner ui-banner--${variant}`} role="status">
      {children}
    </div>
  );
}

export function Breadcrumbs({ items }) {
  if (!items?.length) return null;
  return (
    <nav className="breadcrumbs" aria-label="Навигация">
      <ol className="breadcrumbs__list">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={item.label} className="breadcrumbs__item">
              {!last && item.to ? (
                <Link to={item.to} className="breadcrumbs__link">
                  {item.label}
                </Link>
              ) : (
                <span className="breadcrumbs__current" aria-current={last ? "page" : undefined}>
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function PageHeader({ kicker, title, subtitle, back, actions }) {
  return (
    <header className="page-header ui-lift">
      <div className="page-header__main">
        {back ? (
          <Link className="page-header__back" to={back.to}>
            ← {back.label}
          </Link>
        ) : null}
        {kicker ? <p className="page-header__kicker">{kicker}</p> : null}
        <h1 className="app-title">{title}</h1>
        {subtitle ? <p className="page-header__subtitle">{subtitle}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}
