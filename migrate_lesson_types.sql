-- Миграция для добавления типов занятий
-- Добавляем поля lesson_type и duration_minutes в таблицу schedule

ALTER TABLE schedule 
ADD COLUMN lesson_type VARCHAR(20) DEFAULT 'regular' COMMENT 'Тип занятия: regular или trial',
ADD COLUMN duration_minutes INT DEFAULT 60 COMMENT 'Продолжительность занятия в минутах';

-- Обновляем существующие записи (устанавливаем 60 минут для всех существующих занятий)
UPDATE schedule SET duration_minutes = 60 WHERE duration_minutes IS NULL;