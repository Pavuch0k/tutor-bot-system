-- Миграция для добавления настроек напоминаний репетиторам

-- Добавляем колонки, если их нет
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'telegram_id' AND COLUMN_NAME = 'tutor_notify_day' AND TABLE_SCHEMA = DATABASE());

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE telegram_id
        ADD COLUMN tutor_notify_day BOOLEAN DEFAULT TRUE,
        ADD COLUMN tutor_notify_hour BOOLEAN DEFAULT TRUE,
        ADD COLUMN tutor_notify_10min BOOLEAN DEFAULT TRUE',
    'SELECT "Columns already exist"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Устанавливаем значения по умолчанию для существующих записей
UPDATE telegram_id SET
    tutor_notify_day = TRUE,
    tutor_notify_hour = TRUE,
    tutor_notify_10min = TRUE
WHERE tutor_notify_day IS NULL;
