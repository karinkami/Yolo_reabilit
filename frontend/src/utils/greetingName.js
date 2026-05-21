/** Типичные окончания отчества */
const PATRONYMIC_RE = /(ович|евич|овна|евна|ична|ьич|ич)$/i;

/**
 * Для приветствия: «Имя Отчество» из полного ФИО.
 * «Марданова Карина Ильдаровна» → «Карина Ильдаровна»
 * «Карина Ильдаровна» → без изменений
 */
export function greetingNameFromFio(fullName) {
  const raw = (fullName || "").trim().replace(/\s+/g, " ");
  if (!raw) return "";

  const parts = raw.split(" ");
  if (parts.length >= 3) {
    return `${parts[1]} ${parts.slice(2).join(" ")}`.trim();
  }
  if (parts.length === 2) {
    if (PATRONYMIC_RE.test(parts[1])) {
      return raw;
    }
    return parts[1];
  }
  return parts[0];
}
