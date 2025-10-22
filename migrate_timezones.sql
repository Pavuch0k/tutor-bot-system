-- Миграция часовых поясов из старого формата в новый
-- Обновляем все записи с старым форматом (+04:00, UTC+4 и т.д.) на Europe/Saratov

UPDATE telegram_id 
SET timezone = 'Europe/Saratov' 
WHERE timezone LIKE '+%' OR timezone LIKE 'UTC%' OR timezone IS NULL;

-- Проверяем результат
SELECT id, telegram_id, description, timezone FROM telegram_id;

