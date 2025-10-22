#!/bin/bash

echo "🚀 Настройка проекта Мой учитель"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл из примера..."
    cp .env.example .env
    echo "⚠️  Пожалуйста, отредактируйте .env файл и добавьте ваши настройки"
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

# Применяем миграции
echo "🗄️ Применяем миграции базы данных..."
docker exec my_teacher_mysql mysql -uroot -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} < init_db.sql

# Применяем миграцию часовых поясов
echo "🌍 Применяем миграцию часовых поясов..."
docker exec my_teacher_mysql mysql -uroot -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} < migrate_timezones.sql

# Сбрасываем пароль администратора
echo "🔐 Устанавливаем пароль администратора..."
docker exec my_teacher_web python /app/scripts/fix_admin_password.py admin

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