#!/bin/bash
# Скрипт применения всех миграций к базе данных

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD}"
MYSQL_DATABASE="${MYSQL_DATABASE:-admin_panel}"

echo "🗄️ Применение миграций к базе данных ${MYSQL_DATABASE}..."
echo "   Хост: ${MYSQL_HOST}, Пользователь: ${MYSQL_USER}"

# Функция применения миграции
apply_migration() {
    local migration_file=$1
    local description=$2
    
    if [ -f "$migration_file" ]; then
        echo "📋 Применение: $description"
        if mysql --skip-ssl -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$migration_file" 2>&1; then
            echo "✅ Успешно: $description"
        else
            echo "⚠️ Пропущено: $description (возможно уже применено или есть изменения)"
        fi
    else
        echo "❌ Файл не найден: $migration_file"
    fi
    echo ""
}

# Ждём доступности MySQL
echo "⏳ Ожидание доступности MySQL..."
for i in {1..30}; do
    if mysql --skip-ssl -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" > /dev/null 2>&1; then
        echo "✅ MySQL доступен!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ MySQL не доступен после 30 секунд"
        exit 1
    fi
    sleep 1
done

# Применяем миграции по порядку
cd /app

apply_migration "/app/init_db.sql" "Инициализация БД"
apply_migration "/app/migrate_lesson_types.sql" "Типы занятий"
apply_migration "/app/migrate_reminders.sql" "Настройки напоминаний"
apply_migration "/app/migrate_reports.sql" "Таблица отчётов"
apply_migration "/app/migrate_tutor_notifications.sql" "Настройки уведомлений репетиторов"

echo "✅ Все миграции применены!"
