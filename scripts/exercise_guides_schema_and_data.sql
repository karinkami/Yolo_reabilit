-- Инструкции к упражнениям в PostgreSQL.
-- Синхронизировано с app/exercise_guides_defaults.py
-- Пересоздать: python scripts/export_exercise_guides_sql.py
--
-- Запускайте после сида упражнений (run.py или init_database.py).

BEGIN;

CREATE TABLE IF NOT EXISTS exercise_guides (
  id SERIAL PRIMARY KEY,
  exercise_id INTEGER NOT NULL UNIQUE REFERENCES exercises (id) ON DELETE CASCADE,
  title VARCHAR(300) NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  what_counts TEXT NOT NULL DEFAULT '',
  how_to JSONB NOT NULL DEFAULT '[]'::jsonb,
  mistakes JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- shoulder_abduction
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Отведение руки в сторону',
  'Рука уходит от бедра в сторону, локоть слегка согнут, кисть ниже уровня плеча в комфортной фазе.',
  'Повтор засчитывается при полном цикле отведения в сторону и возврата. Контроль по углу между бедром, плечом и локтем.',
  '["Встаньте боком к камере: рабочая сторона ближе к объективу, в кадре плечо, локоть и кисть.", "Исходное положение: рука свободно вдоль бедра, ладонь к корпусу.", "Отводите руку в сторону от силуэта корпуса по дуге, как будто отодвигаете лёгкий предмет локтем.", "Локоть не разворачивайте резко «вниз»; предплечье остаётся естественным продолжением линии.", "В верхней точке не форсируйте высоту — остановитесь, если чувствуете натяжение или боль.", "Возвращайте руку вниз медленно, контролируя плечо."]'::jsonb,
  '["Наклон туловища в противоположную сторону.", "Поднимать плечо «вверх к уху» вместо отведения.", "Слишком быстрый темп — система попросит замедлиться."]'::jsonb
FROM exercises e WHERE e.key = 'shoulder_abduction'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- recovery_abduction
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Короткое отведение в сторону',
  'Малая амплитуда отведения — реабилитационный вариант без широкого жеста.',
  'Малый цикл в сторону и назад. Засчитывается полный подъём и возврат вниз в небольшой амплитуде (по углу бедро—плечо—локоть).',
  '["Встаньте боком к камере, рабочая рука в кадре.", "Рука у бедра, локоть слегка согнут.", "Отводите на 20–40° в сторону от корпуса или до комфортного предела врача.", "Корпус строго вертикально, взгляд вперёд.", "Возврат медленный, без падения руки «под собственный вес» рывком."]'::jsonb,
  '["Наклон головы на рабочую сторону.", "Резкое увеличение амплитуды."]'::jsonb
FROM exercises e WHERE e.key = 'recovery_abduction'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- forward_raise
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Подъём руки вперёд',
  'Стоя боком к камере: рабочая сторона ближе к объективу. Рука вперёд-вверх от бедра и вниз — повтор при опускании.',
  'Полный цикл: рука внизу у бедра → подъём вперёд-вверх → опускание вниз. Счётчик увеличивается, когда рука возвращается вниз после подъёма.',
  '["Встаньте боком к камере на 1,5–2,5 м: рабочая сторона ближе к объективу, в кадре плечо, локоть и кисть.", "Силуэт корпуса сбоку; вес на обе стопы, корпус прямой.", "Исходное положение: рабочая рука опущена вдоль бедра.", "Поднимайте руку вперёд и немного вверх (не в сторону от корпуса), локоть может быть слегка согнут.", "В верхней точке — комфортная высота без боли и без запрокидывания корпуса назад.", "Опускайте руку по той же линии вниз к бедру — плавно; на опускании засчитывается повтор."]'::jsonb,
  '["Стоять лицом или спиной к камере — угол плеча считается неверно.", "Отводить руку в сторону вместо движения вперёд-вверх.", "Поднимать только кисть, не включая плечо.", "Слишком быстрый темп — дождитесь паузы внизу перед следующим подъёмом."]'::jsonb
FROM exercises e WHERE e.key = 'forward_raise'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- scaption_raise
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Скапционный подъём (плоскость лопатки)',
  'Дуга между «вперёд» и «в сторону»: большой палец слегка вверх, локоть ведёт движение по плоскости лопатки.',
  'Повтор — полный цикл от исхода внизу до верхней точки дуги и возврата. Угол считается по цепочке бедро—плечо—локоть.',
  '["Встаньте боком к камере; рабочая рука вдоль бедра, плечи опущены.", "Поднимайте руку по дуге между «в сторону от корпуса» и «вверх вперёд».", "Локоть чуть в сторону от корпуса; запястье не «ломайте».", "Вверху — короткая пауза без задержки дыхания.", "Опускайте так же плавно, корпус не запрокидывайте назад."]'::jsonb,
  '["Увести руку слишком в сторону (чистое отведение) или слишком вперёд.", "Поднимать плечо к уху.", "Слишком быстрый цикл — система попросит паузу внизу."]'::jsonb
FROM exercises e WHERE e.key = 'scaption_raise'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- arm_raise
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Подъём руки вверх',
  'Работают плечевой сустав и лопатка. Локоть почти выпрямлен, движение плавное.',
  'Один повтор — полный цикл: рука внизу → подъём вверх → возврат вниз. Угол считается по цепочке плечо—локоть—кисть.',
  '["Встаньте боком к камере: рабочая рука в кадре (плечо, локоть, кисть).", "Грудная клетка слегка приподнята, лопатки мягко вниз (не вперёд к ушам).", "Медленно поднимайте руку вверх в комфортной амплитуде; локоть можно чуть согнуть.", "В верхней точке короткая пауза (~1 с), затем так же медленно опустите руку.", "Дышите ровно, без задержки дыхания в крайних точках."]'::jsonb,
  '["Поднимать плечо к уху и напрягать шею.", "Резкий рывок или «бросание» руки вниз.", "Наклон корпуса в сторону или назад."]'::jsonb
FROM exercises e WHERE e.key = 'arm_raise'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- breathing_arms
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Дыхание: подъём обеих рук',
  'Одновременный мягкий подъём и опускание обеих рук в связке с спокойным дыханием.',
  'Один цикл — обе руки подняли и опустили синхронно, с паузой между циклами. Счётчик считает только при достаточно медленном темпе.',
  '["Встаньте боком или четвертью поворотом к камере на 2–3 м, ноги по ширине плеч.", "Исход: обе руки в кадре от плеча до кисти, движения синхронно.", "На вдохе обе руки одновременно поднимаются по дуге; на выдохе — опускаются плавно.", "Поднимайте руки симметрично: разница высоты между руками не должна быть большой.", "Темп медленный; при головокружении или одышке — остановка."]'::jsonb,
  '["Поднимать сильно только одну руку — сломается анализ симметрии.", "Частые рывкообразные качки вместо связки с дыханием.", "Руки не целиком в кадре или слишком тёмное для камеры."]'::jsonb
FROM exercises e WHERE e.key = 'breathing_arms'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- breathing_arms_slow
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Дыхание: медленные циклы с руками',
  'Тот же паттерн, что и «подъём обеих рук», но длиннее фазы — больше акцент на спокойствие и переносимость.',
  'Один повтор — полный медленный цикл подъёма и опускания обеих рук синхронно.',
  '["Встаньте боком или четвертью поворотом: обе цепочки плечо—локоть—кисть в кадре.", "Растяните вдох на подъём, выдох на опускание; не задерживайте дыхание внизу.", "Симметрия рук важнее скорости; при асимметрии уменьшите амплитуду.", "При головокружении сделайте паузу или прекратите серию."]'::jsonb,
  '["Слишком быстрый темп — система попросит замедлить цикл.", "Одна рука заметно выше другой.", "Нет полного обзора обеих рук в кадре."]'::jsonb
FROM exercises e WHERE e.key = 'breathing_arms_slow'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- elbow_flexion
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Сгибание в локте',
  'Предплечье поднимается к плечу, плечо и корпус неподвижны — классическое укрепление сгибателей локтя.',
  'Повтор — полный цикл: рука выпрямлена внизу → сгибание → возврат вниз. Угол по плечо—локоть—кисть.',
  '["Встаньте боком к камере, локоть прижат к корпусу, предплечье вдоль туловища.", "Медленно сгибайте локоть, подводя кисть к плечу, не отводя плечо в сторону.", "В верхней точке — короткая пауза без задержки дыхания.", "Опускайте предплечье так же плавно до почти выпрямленной руки."]'::jsonb,
  '["Отводить плечо в сторону или вперёд вместо работы локтя.", "Раскачивать корпус назад для «помощи».", "Слишком быстрый темп."]'::jsonb
FROM exercises e WHERE e.key = 'elbow_flexion'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- knee_extension
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Разгибание колена (сидя)',
  'Из согнутого колена нога выпрямляется вперёд — укрепление передней поверхности бедра.',
  'Повтор — сгиб → разгиб до почти прямой ноги → возврат в сгиб. Угол бедро—колено—стопа.',
  '["Сядьте в профиль к камере, спина ровная, бедро–колено–стопа рабочей ноги в кадре.", "Исход: колено согнуто под углом около 90°.", "Медленно разгибайте ногу до почти прямого колена, стопа не дёргается.", "Плавно согните колено обратно, не бросая стопу вниз."]'::jsonb,
  '["Запрокидывание корпуса назад при разгибании.", "Резкий рывок в конечных точках.", "Нога частично вне кадра."]'::jsonb
FROM exercises e WHERE e.key = 'knee_extension'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

-- partial_squat
INSERT INTO exercise_guides (exercise_id, title, summary, what_counts, how_to, mistakes)
SELECT e.id,
  'Частичное приседание',
  'Контроль сгибания колена в частичной амплитуде. Выполняется стоя, боком (в профиль) к камере — рабочая нога ближе к объективу.',
  'Один повтор — контролируемое сгибание в колене и возврат в почти выпрямленную ногу. Угол по цепочке бедро—колено—щиколотка рабочей ноги.',
  '["Встаньте боком к камере (в профиль): рабочая нога ближе к объективу, в кадре бедро, колено и щиколотка этой ноги.", "Стопы на ширине плеч, пятки на полу; при опускании таз слегка назад.", "Медленно сгибайте колено до комфортной глубины без острой боли; спина нейтральная, взгляд вперёд.", "Поднимайтесь вверх через пятки и ягодицы, не отрывая пятки и не рывком."]'::jsonb,
  '["Стоять лицом или спиной к камере — система не видит угол колена.", "Резкий наклон корпуса вперёд без контроля.", "Колено сильно заваливается внутрь или уходит далеко за носок.", "Бедро, колено или щиколотка вне кадра."]'::jsonb
FROM exercises e WHERE e.key = 'partial_squat'
ON CONFLICT (exercise_id) DO UPDATE SET
  title = EXCLUDED.title, summary = EXCLUDED.summary, what_counts = EXCLUDED.what_counts,
  how_to = EXCLUDED.how_to, mistakes = EXCLUDED.mistakes;

COMMIT;
