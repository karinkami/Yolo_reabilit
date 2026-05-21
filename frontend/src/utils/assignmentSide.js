/** Подписи стороны назначения (от врача). */



const DUAL_ARM_KEYS = new Set(["breathing_arms", "breathing_arms_slow"]);

const LEG_KEYS = new Set(["partial_squat", "knee_extension"]);



export function isLegExercise(exerciseKey) {

  return LEG_KEYS.has(exerciseKey);

}



export function isDualArmExercise(exerciseKey) {

  return DUAL_ARM_KEYS.has(exerciseKey);

}



export function isPartialSquat(exerciseKey) {

  return exerciseKey === "partial_squat";

}



export function complexComposeSideHint(item) {

  return isDualArmExercise(item?.exercise_key) ? "обе руки" : null;

}



export function sideLabelFull(side, exerciseKey) {

  if (isDualArmExercise(exerciseKey)) return "Обе руки";

  if (isPartialSquat(exerciseKey)) return "Стоя боком";

  const limb = isLegExercise(exerciseKey) ? "нога" : "рука";

  const adj = side === "left" ? "Левая" : "Правая";

  return `${adj} ${limb}`;

}



export function sideInstrumentalPhrase(side, exerciseKey) {

  if (isDualArmExercise(exerciseKey)) return "обеими руками";

  if (side === "left") return isLegExercise(exerciseKey) ? "левой ногой" : "левой рукой";

  return isLegExercise(exerciseKey) ? "правой ногой" : "правой рукой";

}



export function sideImperative(side, exerciseKey) {

  if (isDualArmExercise(exerciseKey)) {
    return "Встаньте боком к камере. Двигайте обе руки синхронно";
  }

  if (isPartialSquat(exerciseKey)) return "Встаньте боком к камере";

  const limb = isLegExercise(exerciseKey) ? "ногу" : "руку";

  return side === "left"
    ? `Встаньте боком к камере. Используйте левую ${limb}`
    : `Встаньте боком к камере. Используйте правую ${limb}`;

}



export function bothSidesAssignLabel(exerciseKey) {

  if (isPartialSquat(exerciseKey)) return "Два подхода боком";

  if (isLegExercise(exerciseKey)) return "Обе ноги";

  return "Обе руки";

}



export function sidePrepareMessage(side, exerciseKey) {

  if (isDualArmExercise(exerciseKey)) {

    return "Подготовьтесь: встаньте боком к камере, двигайте обе руки синхронно.";

  }

  if (isPartialSquat(exerciseKey)) {

    return (

      "Встаньте боком к камере — рабочая нога ближе к объективу. " +

      "Подготовьтесь к приседанию: бедро, колено и щиколотка в кадре."

    );

  }

  return (
    `Встаньте боком к камере, работайте ${sideInstrumentalPhrase(side, exerciseKey)}. ` +
    "Подготовьтесь к выполнению упражнения."
  );

}



export function formatAssignmentSide(side, exerciseKey) {

  return sideLabelFull(side, exerciseKey);

}



export function bundleQueueHint(queueIndex, queueLength, side, exerciseKey) {

  if (isPartialSquat(exerciseKey) && queueLength > 1) {

    return `Стоя боком (${queueIndex + 1} из ${queueLength})`;

  }

  if (queueLength <= 1) return sideLabelFull(side, exerciseKey);

  const ord = queueIndex + 1;

  return `${sideLabelFull(side, exerciseKey)} (${ord} из ${queueLength})`;

}



/** Игнорирует устаревшие подписи с API («Позиция 1/2»). */

export function resolveSideLabel(side, exerciseKey, fromApi) {

  if (isPartialSquat(exerciseKey)) return sideLabelFull(side, exerciseKey);

  if (fromApi && !/позици/i.test(fromApi)) return fromApi;

  return sideLabelFull(side, exerciseKey);

}



export function resolveSideImperative(side, exerciseKey, fromApi) {

  if (isPartialSquat(exerciseKey)) {
    return sideImperative(side, exerciseKey);
  }

  if (fromApi && !/позици|боком/i.test(fromApi)) return fromApi;

  return sideImperative(side, exerciseKey);

}

