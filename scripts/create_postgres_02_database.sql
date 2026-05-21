-- Шаг 2 из 2. CREATE DATABASE нельзя выполнять в одной транзакции с другими командами.
--
-- Вариант A (удобнее всего): в pgAdmin правый клик по Databases → Create → Database:
--   Name: yolo_rehab
--   Owner: yolo_rehab
--   Encoding: UTF8
--
-- Вариант B: откройте НОВЫЙ Query Tool (под postgres), вставьте ТОЛЬКО одну команду ниже
-- (без других строк), включите Autocommit если есть, и выполните F5.

CREATE DATABASE yolo_rehab
    OWNER yolo_rehab
    ENCODING 'UTF8'
    TEMPLATE template0;
