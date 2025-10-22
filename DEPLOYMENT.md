# Развертывание проекта Tutor Bot System

## CI/CD Pipeline

Проект использует GitHub Actions для автоматической сборки и развертывания.

### Переменные окружения в GitHub Secrets

Необходимо добавить следующие секреты в репозитории GitHub:

```
DOCKER_USERNAME      # Имя пользователя Docker Hub
DOCKER_PASSWORD      # Пароль от Docker Hub
HOST                 # IP адрес сервера
USERNAME             # Пользователь на сервере
SSH_KEY              # Приватный SSH ключ
```

### Структура CI/CD

1. **Test** - Запускает тесты и проверку кода
2. **Build and Deploy** - Собирает Docker образы и развертывает на сервер
3. **Security Scan** - Проверяет уязвимости

## Ручное развертывание

### Требования

- Docker и Docker Compose
- MySQL 8.0
- Python 3.12+

### Шаги развертывания

1. **Клонирование репозитория**
   ```bash
   git clone git@github.com:Pavuch0k/tutor-bot-system.git
   cd tutor-bot-system
   ```

2. **Настройка переменных окружения**
   ```bash
   cp .env.example .env
   # Отредактируйте .env с вашими данными
   ```

3. **Запуск через Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Инициализация базы данных**
   ```bash
   docker-compose exec flask python -c "
   from app import app, db
   with app.app_context():
       db.create_all()
   "
   ```

### Структура проекта

```
├── .github/workflows/    # GitHub Actions
├── tests/               # Тесты
├── templates/           # HTML шаблоны
├── static/              # Статические файлы
├── scripts/             # Скрипты настройки
├── Dockerfile           # Образ для Flask приложения
├── Dockerfile.bot       # Образ для Telegram бота
├── docker-compose.yml   # Оркестрация контейнеров
└── app.py              # Основное приложение
```

### Мониторинг

- **Логи**: `docker-compose logs -f`
- **Статус**: `docker-compose ps`
- **Перезапуск**: `docker-compose restart`

### Безопасность

- Все секреты хранятся в GitHub Secrets
- `.env` файл исключен из git
- Используются HTTPS соединения
- Регулярные проверки безопасности через Trivy