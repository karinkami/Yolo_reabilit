-- Выполнять в psql / pgAdmin как SQL, НЕ через открытие .py файлов.
-- Либо просто запустить Flask — schema_patch.py применит то же самое.
--
-- PostgreSQL 11+:
ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS birth_date DATE;
ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS comorbidities TEXT DEFAULT '';
ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS full_name_official VARCHAR(200) DEFAULT '';
