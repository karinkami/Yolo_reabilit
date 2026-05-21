/**
 * Даты с сервера — UTC в ISO с суффиксом Z (см. app/datetime_util.utc_iso_z).
 * Показ в интерфейсе — в локальном часовом поясе браузера.
 */

export function parseUtcIso(iso) {
  if (iso == null || iso === "") return null;
  const raw = String(iso).trim();
  if (!raw) return null;
  const hasTz = /[zZ]$/.test(raw) || /[+-]\d{2}:\d{2}$/.test(raw);
  const normalized =
    hasTz || !raw.includes("T") ? raw : `${raw}Z`;
  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDateTimeLocal(iso) {
  const d = parseUtcIso(iso);
  if (!d) return "—";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Календарные «сегодня / вчера» в локальном поясе. */
export function formatRelativeDayRu(iso) {
  const d = parseUtcIso(iso);
  if (!d) return null;
  const startOfDay = (dt) => new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
  const days = Math.floor((startOfDay(new Date()) - startOfDay(d)) / 86400000);
  if (days < 0) return "недавно";
  if (days === 0) return "сегодня";
  if (days === 1) return "вчера";
  if (days < 7) return `${days} дн. назад`;
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}
