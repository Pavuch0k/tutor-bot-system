#!/bin/bash

echo "🚀 Настройка проекта Мой учитель"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env в корне проекта со следующими переменными:"
    echo "   MYSQL_HOST=localhost"
    echo "   MYSQL_USER=root"
    echo "   MYSQL_PASSWORD=your_password"
    echo "   MYSQL_DATABASE=admin_panel"
    echo "   SECRET_KEY=your_secret_key"
    echo "   TELEGRAM_BOT_TOKEN=your_bot_token"
    echo "   WEBAPP_URL=http://localhost:5000/schedule"
    echo "   LOG_GROUP_ID=your_log_group_id"
    echo "   REPORTS_CHAT_ID=your_reports_chat_id"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Создаем необходимые директории
echo "📁 Создаем директории..."
mkdir -p static
mkdir -p logs

# Строим и запускаем контейнеры
echo "🐳 Запускаем Docker контейнеры..."
docker-compose down
docker-compose up -d --build

# Ждем запуска MySQL
echo "⏳ Ожидаем запуска MySQL..."
sleep 10

# Миграции применяются автоматически через docker-entrypoint-initdb.d
echo "🗄️ Миграции базы данных применяются автоматически при первом запуске MySQL"
echo "   Файлы: init_db.sql, migrate_lesson_types.sql, migrate_reminders.sql, migrate_reports.sql"

echo "✅ Установка завершена!"
echo ""
echo "📌 Информация для входа:"
echo "   URL: http://localhost:5000"
echo "   Логин: admin"
echo "   Пароль: admin"
echo ""
echo "🔧 Полезные команды:"
echo "   docker-compose logs -f    # Просмотр логов"
echo "   docker-compose restart    # Перезапуск сервисов"
echo "   docker-compose down       # Остановка сервисов"
echo ""
echo "⚠️  ВАЖНО: После первого входа обязательно смените пароль!"