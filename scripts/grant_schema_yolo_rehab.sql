-- Выполнять в pgAdmin под СУПЕРПОЛЬЗОВАТЕЛЕМ (postgres).
-- В дереве сначала выберите базу yolo_rehab, затем Query Tool — чтобы запрос шёл в эту БД.
-- После этого приложение сможет выполнить CREATE TABLE (db.create_all).

GRANT USAGE, CREATE ON SCHEMA public TO yolo_rehab;

-- Явно делаем владельцем схемы public вашу роль (часто решает проблему в PostgreSQL 15+).
ALTER SCHEMA public OWNER TO yolo_rehab;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO yolo_rehab;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO yolo_rehab;
