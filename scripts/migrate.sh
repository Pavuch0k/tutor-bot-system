#!/bin/bash
# Скрипт для автоматического применения миграций

echo "Проверка миграций базы данных..."

# Проверяем переменные окружения
if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_PASSWORD" ] || [ -z "$MYSQL_DATABASE" ]; then
    echo "Ошибка: Не все переменные окружения установлены"
    exit 1
fi

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
    if [ $? -eq 0 ]; then
        echo "Миграция типов занятий применена успешно"
    else
        echo "Ошибка при применении миграции типов занятий"
        exit 1
    fi
fi

if [ -f "/app/migrate_timezones.sql" ]; then
    echo "Применение миграции часовых поясов..."
    mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < /app/migrate_timezones.sql
    if [ $? -eq 0 ]; then
        echo "Миграция часовых поясов применена успешно"
    else
        echo "Ошибка при применении миграции часовых поясов"
        exit 1
    fi
fi

echo "Все миграции завершены успешно"
exit 0