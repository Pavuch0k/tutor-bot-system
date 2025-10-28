-- Миграция для добавления типа занятия и продолжительности
-- Обновление существующих занятий

-- Добавляем колонки, если их нет
SET @col_exists_lesson_type = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'schedule' AND COLUMN_NAME = 'lesson_type' AND TABLE_SCHEMA = DATABASE());
    
SET @col_exists_duration = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'schedule' AND COLUMN_NAME = 'duration_minutes' AND TABLE_SCHEMA = DATABASE());

SET @sql = IF(@col_exists_lesson_type = 0, 
    'ALTER TABLE schedule ADD COLUMN lesson_type VARCHAR(20) DEFAULT "regular"', 
    'SELECT "Column lesson_type already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(@col_exists_duration = 0, 
    'ALTER TABLE schedule ADD COLUMN duration_minutes INT DEFAULT 60', 
    'SELECT "Column duration_minutes already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Устанавливаем для всех существующих занятий тип 'regular' и продолжительность 60 минут
UPDATE schedule SET lesson_type = 'regular' WHERE lesson_type IS NULL OR lesson_type = '';
UPDATE schedule SET duration_minutes = 60 WHERE duration_minutes IS NULL;

