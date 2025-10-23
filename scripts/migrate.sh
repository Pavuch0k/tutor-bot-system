#!/bin/bash
# Скрипт для автоматического применения миграций

echo "Проверка миграций базы данных..."

# Ожидаем запуска MySQL
echo "Ожидание доступности MySQL..."
while ! mysqladmin ping -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --silent; do
    sleep 2
done
echo "MySQL доступен"

# Применяем миграции если они существуют
if [ -f "/app/migrate_lesson_types.sql" ]; then
    echo "Применение миграции типов занятий..."
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < /app/migrate_lesson_types.sql
    echo "Миграция типов занятий применена"
fi

if [ -f "/app/migrate_timezones.sql" ]; then
    echo "Применение миграции часовых поясов..."
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < /app/migrate_timezones.sql
    echo "Миграция часовых поясов применена"
fi

echo "Миграции завершены"