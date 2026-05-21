/** Актуальный каталог комплексов (синхронно с app/exercise_catalog.py). */

export const COMPLEX_CATALOG_VERSION = 4;

export const ASSIGNMENT_COMPLEX_IDS = [
  "complex_breathing",
  "complex_shoulder_early",
  "complex_shoulder_full",
  "complex_lower_limb",
  "complex_full_body",
];

const ALLOWED = new Set(ASSIGNMENT_COMPLEX_IDS);

/** Убирает устаревшие/дублирующие комплексы с сервера. */
export function filterAssignmentComplexes(list) {
  if (!Array.isArray(list)) return [];
  const seen = new Set();
  const out = [];
  for (const id of ASSIGNMENT_COMPLEX_IDS) {
    const c = list.find((x) => x?.id === id);
    if (c && !seen.has(id)) {
      seen.add(id);
      out.push(c);
    }
  }
  return out;
}

export function isAllowedComplexId(id) {
  return ALLOWED.has(id);
}

/** Пять разных упражнений в списке «Одно упражнение» (синхронно с DOCTOR_PICKER_EXERCISE_KEYS). */
export const DOCTOR_PICKER_EXERCISE_KEYS = [
  "breathing_arms",
  "shoulder_abduction",
  "scaption_raise",
  "forward_raise",
  "elbow_flexion",
  "partial_squat",
];

const PICKER_KEYS = new Set(DOCTOR_PICKER_EXERCISE_KEYS);

export function filterDoctorExercises(list) {
  if (!Array.isArray(list)) return [];
  return list.filter((e) => PICKER_KEYS.has(e.key));
}
