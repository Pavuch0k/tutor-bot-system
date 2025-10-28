#!/bin/bash
# Скрипт для очистки старых данных БД перед обновлением

echo "🧹 Очистка старых данных..."

# Останавливаем контейнеры
echo "⏹️ Остановка контейнеров..."
docker-compose down

# Удаляем volume с данными MySQL
echo "🗑️ Удаление старого объема MySQL..."
docker volume rm my_teacher_mysql_data 2>/dev/null || true

# Удаляем образы для полной пересборки
echo "🗑️ Удаление старых образов..."
docker rmi my_teacher-web my_teacher-bot 2>/dev/null || true

echo "✅ Очистка завершена. Можно запускать docker-compose up -d"

