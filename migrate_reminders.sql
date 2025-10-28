-- Миграция для добавления настроек напоминаний

-- Добавляем колонки, если их нет
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'telegram_id' AND COLUMN_NAME = 'student_notify_day' AND TABLE_SCHEMA = DATABASE());

SET @sql = IF(@col_exists = 0, 
    'ALTER TABLE telegram_id 
        ADD COLUMN student_notify_day BOOLEAN DEFAULT TRUE,
        ADD COLUMN student_notify_hour BOOLEAN DEFAULT TRUE,
        ADD COLUMN student_notify_10min BOOLEAN DEFAULT TRUE,
        ADD COLUMN parent_notify_day BOOLEAN DEFAULT TRUE,
        ADD COLUMN parent_notify_hour BOOLEAN DEFAULT TRUE,
        ADD COLUMN parent_notify_10min BOOLEAN DEFAULT TRUE', 
    'SELECT "Columns already exist"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Устанавливаем значения по умолчанию для существующих записей
UPDATE telegram_id SET 
    student_notify_day = TRUE,
    student_notify_hour = TRUE,
    student_notify_10min = TRUE,
    parent_notify_day = TRUE,
    parent_notify_hour = TRUE,
    parent_notify_10min = TRUE
WHERE student_notify_day IS NULL;

