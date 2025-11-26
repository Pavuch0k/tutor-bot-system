# Переменные окружения

## Список всех переменных окружения, используемых в проекте

### Обязательные переменные

#### База данных MySQL
- **MYSQL_HOST** - хост MySQL (по умолчанию: `localhost`, в Docker: `mysql`)
- **MYSQL_USER** - пользователь MySQL (обычно: `root`)
- **MYSQL_PASSWORD** - пароль MySQL
- **MYSQL_DATABASE** - имя базы данных (обычно: `admin_panel`)

#### Flask приложение (web)
- **SECRET_KEY** - секретный ключ для Flask сессий

#### Telegram бот
- **TELEGRAM_BOT_TOKEN** - токен Telegram бота (обязательно)
- **WEBAPP_URL** - URL веб-приложения для расписания (по умолчанию: `http://localhost:5000/schedule`)
- **LOG_GROUP_ID** - ID Telegram группы для отправки логов
- **REPORTS_CHAT_ID** - ID Telegram чата для отправки отчётов на подтверждение

### Дополнительные переменные

#### Docker Compose
- **TZ** - часовой пояс для контейнера бота (в docker-compose.yml жестко задано: `Asia/Dubai`)

## Где используются переменные

### bot.py
- `TELEGRAM_BOT_TOKEN` - токен бота
- `WEBAPP_URL` - URL веб-приложения
- `LOG_GROUP_ID` - ID группы для логов
- `REPORTS_CHAT_ID` - ID чата для отчётов
- `MYSQL_HOST` - хост БД (по умолчанию: `localhost`)
- `MYSQL_USER` - пользователь БД
- `MYSQL_PASSWORD` - пароль БД
- `MYSQL_DATABASE` - имя БД

### app.py
- `SECRET_KEY` - секретный ключ Flask
- `MYSQL_HOST` - хост БД
- `MYSQL_USER` - пользователь БД
- `MYSQL_PASSWORD` - пароль БД
- `MYSQL_DATABASE` - имя БД

### docker-compose.yml
Все переменные передаются в контейнеры через `${VAR_NAME}` синтаксис.

### GitHub Actions (.github/workflows/ci-cd.yml)
При деплое на сервер создаётся `.env` файл из GitHub Secrets:
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE` (жестко: `admin_panel`)
- `MYSQL_USER` (жестко: `root`)
- `SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`
- `WEBAPP_URL` (жестко: `https://admin.tvoi-uchitel.ru/schedule`)
- `LOG_GROUP_ID`
- `REPORTS_CHAT_ID`

## Локальная разработка

Для локальной разработки создайте файл `.env` в корне проекта со следующими переменными:

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=admin_panel
SECRET_KEY=your_secret_key
TELEGRAM_BOT_TOKEN=your_bot_token
WEBAPP_URL=http://localhost:5000/schedule
LOG_GROUP_ID=your_log_group_id
REPORTS_CHAT_ID=your_reports_chat_id
```

**Важно:** Файл `.env` не должен коммититься в репозиторий (добавлен в `.gitignore`).

## Production

На production сервере `.env` файл создаётся автоматически при деплое через GitHub Actions из GitHub Secrets. Не нужно создавать его вручную.

