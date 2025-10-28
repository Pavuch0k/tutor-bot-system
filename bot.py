#!/usr/bin/env python3
import os
import logging
import sys
from dotenv import load_dotenv
import mysql.connector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import asyncio
from datetime import datetime, timedelta, time
import pytz

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'http://localhost:5000/schedule')
LOG_GROUP_ID = os.getenv('LOG_GROUP_ID')  # ID группы для отправки логов

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# База данных конфигурация
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE')
}

# Часовой пояс системы (Саратов)
SYSTEM_TIMEZONE = pytz.timezone('Europe/Saratov')  # UTC+4

# Доступные часовые пояса для выбора
TIMEZONES = {
    'Europe/Moscow': '🇷🇺 Москва (UTC+3)',
    'Europe/Saratov': '🇷🇺 Саратов (UTC+4)',
    'Asia/Yekaterinburg': '🇷🇺 Екатеринбург (UTC+5)',
    'Asia/Omsk': '🇷🇺 Омск (UTC+6)',
    'Asia/Krasnoyarsk': '🇷🇺 Красноярск (UTC+7)',
    'Asia/Irkutsk': '🇷🇺 Иркутск (UTC+8)',
    'Asia/Yakutsk': '🇷🇺 Якутск (UTC+9)',
    'Asia/Vladivostok': '🇷🇺 Владивосток (UTC+10)',
    'Asia/Magadan': '🇷🇺 Магадан (UTC+11)',
    'Asia/Kamchatka': '🇷🇺 Камчатка (UTC+12)',
    'Europe/Kaliningrad': '🇷🇺 Калининград (UTC+2)',
}

# Функция для проверки пользователя в БД
def get_user_info(username):
    """Получить информацию о пользователе из БД"""
    if not username:
        return None
    
    # Убираем @ если он есть
    if username.startswith('@'):
        username = username[1:]
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM telegram_id WHERE telegram_id = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        return None

# Функция для сохранения chat_id пользователя
def save_chat_id(username, chat_id):
    """Сохранить chat_id пользователя в БД"""
    if not username:
        return False
    
    # Убираем @ если он есть
    if username.startswith('@'):
        username = username[1:]
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE telegram_id SET chat_id = %s WHERE telegram_id = %s",
            (chat_id, username)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении chat_id: {e}")
        return False

async def send_log_to_group(application, message):
    """Отправить логовое сообщение в группу"""
    if not LOG_GROUP_ID:
        return False
    
    try:
        await application.bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=message,
            parse_mode='HTML'
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке лога в группу: {e}")
        return False

def update_user_timezone(username, timezone_str):
    """Обновить часовой пояс пользователя"""
    if not username:
        return False
    
    # Убираем @ если он есть
    if username.startswith('@'):
        username = username[1:]
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE telegram_id SET timezone = %s WHERE telegram_id = %s",
            (timezone_str, username)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении timezone: {e}")
        return False

def convert_time_to_user_timezone(system_datetime, user_timezone_str):
    """
    Конвертировать время из системного часового пояса в пользовательский
    system_datetime - datetime объект в системном времени (Саратов UTC+4)
    user_timezone_str - строка часового пояса пользователя (например, 'Europe/Moscow')
    """
    try:
        # Если передана строка вместо timezone объекта
        if isinstance(user_timezone_str, str):
            if user_timezone_str.startswith('UTC') or user_timezone_str.startswith('+'):
                # Старый формат (например, '+04:00')
                user_timezone_str = 'Europe/Saratov'  # По умолчанию
            user_tz = pytz.timezone(user_timezone_str)
        else:
            user_tz = user_timezone_str
        
        # Локализуем системное время
        system_dt_localized = SYSTEM_TIMEZONE.localize(system_datetime) if system_datetime.tzinfo is None else system_datetime
        
        # Конвертируем в пользовательский часовой пояс
        user_dt = system_dt_localized.astimezone(user_tz)
        
        return user_dt
    except Exception as e:
        logger.error(f"Ошибка конвертации времени: {e}")
        return system_datetime

def get_main_keyboard():
    """Получить главную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("📅 Расписание"), KeyboardButton("⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def set_menu_button(bot, chat_id: int, username: str):
    """Установить кнопку меню для WebApp"""
    try:
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(
                text="📅 Расписание",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?username={username}")
            )
        )
    except Exception as e:
        logger.error(f"Ошибка при установке кнопки меню: {e}")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    logger.info(f"Получена команда /start от пользователя {update.effective_user}")
    
    user = update.effective_user
    username = user.username
    chat_id = update.effective_chat.id

    if not username:
        await update.message.reply_text(
            "❌ Для использования бота необходимо установить username в настройках Telegram.\n\n"
            "Перейдите в Настройки → Изменить профиль → Имя пользователя"
        )
        return

    # Проверяем, есть ли пользователь в базе
    user_info = get_user_info(username)
    
    if user_info:
        # Сохраняем chat_id в базу данных
        save_chat_id(username, chat_id)
        
        # Отправляем лог о входе пользователя
        log_message = (
            f"👤 <b>Вход пользователя</b>\n\n"
            f"🆔 <b>Имя:</b> {user.first_name}\n"
            f"👤 <b>Username:</b> @{username}\n"
            f"📋 <b>Статус:</b> {user_info['status']}\n"
            f"🏷️ <b>Описание:</b> {user_info['description']}\n"
            f"⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await send_log_to_group(context.application, log_message)
        
        # Устанавливаем кнопку меню
        await set_menu_button(context.bot, chat_id, username)
        
        # Формируем приветственное сообщение
        if user_info['status'] == 'репетитор':
            welcome_text = (
                f"👋 Добро пожаловать, {user_info['description']}!\n\n"
                f"📚 Вы авторизованы как репетитор\n\n"
                f"Доступные функции:\n"
                f"• Просмотр расписания занятий\n"
                f"• Уведомления о предстоящих занятиях\n"
                f"• Настройка часового пояса\n\n"
                f"💡 Используйте кнопки ниже для управления"
            )
        else:
            welcome_text = (
                f"👋 Добро пожаловать, {user_info['description']}!\n\n"
                f"🎓 Вы авторизованы как ученик\n\n"
                f"Доступные функции:\n"
                f"• Просмотр расписания занятий\n"
                f"• Уведомления о предстоящих занятиях\n"
                f"• Настройка часового пояса\n\n"
                f"💡 Используйте кнопки ниже для управления"
            )
        
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "👋 Добро пожаловать в образовательную компанию «Твой Учитель»!\n\n"
            "📚 Мы помогаем ученикам достигать высоких результатов в учебе.\n\n"
            "✨ Для записи на пробное занятие обратитесь к администратору: @poliakkk"
        )

# Обработка всех текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка всех текстовых сообщений"""
    logger.info(f"Получено сообщение от пользователя {update.effective_user}: {update.message.text}")
    
    user = update.effective_user
    username = user.username
    chat_id = update.effective_chat.id
    message_text = update.message.text

    if not username:
        await update.message.reply_text(
            "❌ Для использования бота необходимо установить username в настройках Telegram.\n\n"
            "Перейдите в Настройки → Изменить профиль → Имя пользователя"
        )
        return

    # Проверяем, есть ли пользователь в базе
    user_info = get_user_info(username)
    
    if user_info:
        # Сохраняем chat_id в базу данных
        save_chat_id(username, chat_id)
        
        # Устанавливаем кнопку меню
        await set_menu_button(context.bot, chat_id, username)
        
        # Обработка кнопок
        if message_text == "📅 Расписание":
            # Отправляем лог о просмотре расписания
            log_message = (
                f"📅 <b>Просмотр расписания</b>\n\n"
                f"👤 <b>Имя:</b> {update.message.from_user.first_name}\n"
                f"👤 <b>Username:</b> @{username}\n"
                f"📋 <b>Статус:</b> {user_info['status']}\n"
                f"🏷️ <b>Описание:</b> {user_info['description']}\n"
                f"⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await send_log_to_group(context.application, log_message)
            
            # Создаем inline кнопку с WebApp
            keyboard = [
                [InlineKeyboardButton(
                    "📅 Открыть расписание",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}?username={username}")
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text=f"📅 {user_info['description']}, нажмите на кнопку ниже, чтобы открыть ваше расписание:",
                reply_markup=reply_markup
            )
            
        elif message_text == "⚙️ Настройки":
            await show_settings(update, context, user_info)
            
        else:
            # Обработка обычного текста
            await update.message.reply_text(
                text=f"👋 Привет, {user_info['description']}!\n\n"
                     f"Используйте кнопки ниже для управления ботом.",
                reply_markup=get_main_keyboard()
            )
    else:
        # Отправляем только одно сообщение неавторизованным пользователям
        if not context.chat_data.get('denied'):
            await update.message.reply_text(
                "👋 Добро пожаловать в образовательную компанию «Твой Учитель»!\n\n"
                "📚 Мы помогаем ученикам достигать высоких результатов в учебе.\n\n"
                "✨ Для записи на пробное занятие обратитесь к администратору: @poliakkk"
            )
            context.chat_data['denied'] = True

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_info: dict) -> None:
    """Показать настройки пользователя"""
    # Получаем текущий часовой пояс пользователя
    current_tz = user_info.get('timezone', 'Europe/Saratov')
    
    # Если старый формат, конвертируем
    if current_tz.startswith('+') or current_tz.startswith('UTC'):
        current_tz = 'Europe/Saratov'
    
    # Получаем название часового пояса
    current_tz_name = TIMEZONES.get(current_tz, '🇷🇺 Саратов (UTC+4)')
    
    # Создаем inline клавиатуру для выбора часового пояса
    keyboard = []
    for tz_key, tz_name in TIMEZONES.items():
        # Добавляем галочку к текущему часовому поясу
        label = f"✅ {tz_name}" if tz_key == current_tz else tz_name
        keyboard.append([InlineKeyboardButton(label, callback_data=f"tz:{tz_key}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"👤 <b>Имя:</b> {user_info['description']}\n"
        f"🆔 <b>Статус:</b> {user_info['status']}\n"
        f"🌍 <b>Часовой пояс:</b> {current_tz_name}\n\n"
        f"Выберите ваш часовой пояс из списка ниже:"
    )
    
    await update.message.reply_text(
        text=settings_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора часового пояса"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    username = user.username
    
    if not username:
        await query.edit_message_text("❌ Не удалось определить ваш username")
        return
    
    # Получаем выбранный часовой пояс из callback_data
    callback_data = query.data
    if not callback_data.startswith("tz:"):
        return
    
    timezone_str = callback_data[3:]  # Убираем префикс "tz:"
    
    # Обновляем часовой пояс в базе данных
    if update_user_timezone(username, timezone_str):
        timezone_name = TIMEZONES.get(timezone_str, timezone_str)
        
        # Получаем информацию о пользователе
        user_info = get_user_info(username)
        
        # Отправляем лог о смене часового пояса
        if user_info:
            log_message = (
                f"🌍 <b>Смена часового пояса</b>\n\n"
                f"👤 <b>Имя:</b> {query.from_user.first_name}\n"
                f"👤 <b>Username:</b> @{username}\n"
                f"📋 <b>Статус:</b> {user_info['status']}\n"
                f"🌍 <b>Новый часовой пояс:</b> {timezone_name}\n"
                f"⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await send_log_to_group(context.application, log_message)
        
        if user_info:
            # Пересоздаем клавиатуру с обновленной галочкой
            keyboard = []
            for tz_key, tz_name in TIMEZONES.items():
                label = f"✅ {tz_name}" if tz_key == timezone_str else tz_name
                keyboard.append([InlineKeyboardButton(label, callback_data=f"tz:{tz_key}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            settings_text = (
                f"⚙️ <b>Настройки</b>\n\n"
                f"👤 <b>Имя:</b> {user_info['description']}\n"
                f"🆔 <b>Статус:</b> {user_info['status']}\n"
                f"🌍 <b>Часовой пояс:</b> {timezone_name}\n\n"
                f"✅ Часовой пояс успешно обновлен!\n\n"
                f"Выберите ваш часовой пояс из списка ниже:"
            )
            
            await query.edit_message_text(
                text=settings_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(f"✅ Часовой пояс обновлен на {timezone_name}")
    else:
        await query.edit_message_text("❌ Ошибка при обновлении часового пояса")

async def send_reminder(bot, chat_id, schedule_data, user_status, time_before, user_timezone_str):
    """Отправить напоминание о занятии"""
    try:
        # Формируем сообщение в зависимости от времени до занятия
        if time_before == "day":
            emoji = "📅"
            time_text = "завтра"
        elif time_before == "hour":
            emoji = "⏰"
            time_text = "через час"
        else:  # 10 минут
            emoji = "🔔"
            time_text = "через 10 минут"
        
        # Конвертируем время в часовой пояс пользователя
        # schedule_data['time'] - это строка типа "14:30"
        schedule_time_str = schedule_data['time']
        schedule_date = schedule_data.get('date')  # Дата занятия
        
        # Создаем datetime объект в системном времени
        if schedule_date:
            hours, minutes = map(int, schedule_time_str.split(':'))
            system_datetime = datetime.combine(schedule_date, time(hours, minutes))
            
            # Конвертируем в пользовательский часовой пояс
            user_datetime = convert_time_to_user_timezone(system_datetime, user_timezone_str)
            time_display = user_datetime.strftime('%H:%M')
        else:
            time_display = schedule_time_str
        
        # Получаем тип занятия и длительность
        lesson_type = schedule_data.get('lesson_type', 'regular')
        duration = schedule_data.get('duration_minutes', 60)
        is_trial = lesson_type == 'trial'
        
        duration_text = f"{duration} мин." if duration else "60 мин."
        trial_text = "🎯 ПРОБНОЕ " if is_trial else ""
        
        message = f"{emoji} Напоминание: {trial_text}занятие {time_text}!\n\n"
        message += f"📚 Предмет: {schedule_data['subject_name']}\n"
        message += f"🕐 Время: {time_display} ({duration_text})\n"
        
        if user_status == 'репетитор':
            message += f"👤 Ученик: {schedule_data['student_name']}"
        else:
            message += f"👨‍🏫 Репетитор: {schedule_data['tutor_name']}"
        
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Отправлено напоминание пользователю {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")
        return False

async def check_schedules(application):
    """Проверка расписания и отправка напоминаний"""
    sent_reminders = set()
    
    while True:
        try:
            now = datetime.now()
            
            # Подключаемся к БД
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            # Получаем расписание на сегодня и завтра
            today = now.date()
            tomorrow = (now + timedelta(days=1)).date()
            
            cursor.execute("""
                SELECT 
                    s.id, s.date, s.time, s.tutor_id, s.student_id,
                    s.lesson_type, s.duration_minutes,
                    sub.name as subject_name,
                    t1.telegram_id as tutor_username, t1.description as tutor_name, t1.chat_id as tutor_chat_id, t1.timezone as tutor_timezone,
                    t2.telegram_id as student_username, t2.description as student_name, t2.chat_id as student_chat_id, t2.timezone as student_timezone
                FROM schedule s
                JOIN subject sub ON s.subject_id = sub.id
                JOIN telegram_id t1 ON s.tutor_id = t1.id
                JOIN telegram_id t2 ON s.student_id = t2.id
                WHERE s.date IN (%s, %s) AND (t1.chat_id IS NOT NULL OR t2.chat_id IS NOT NULL)
            """, (today, tomorrow))
            
            schedules = cursor.fetchall()
            
            for schedule in schedules:
                # MySQL возвращает TIME как timedelta
                try:
                    if isinstance(schedule['time'], timedelta):
                        # Конвертируем timedelta в time
                        total_seconds = int(schedule['time'].total_seconds())
                        hours = (total_seconds // 3600) % 24
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        schedule_time = time(hours, minutes, seconds)
                    elif isinstance(schedule['time'], str):
                        # Если время пришло как строка HH:MM:SS
                        time_parts = schedule['time'].split(':')
                        schedule_time = time(int(time_parts[0]), int(time_parts[1]), int(time_parts[2]) if len(time_parts) > 2 else 0)
                    else:
                        # Если уже time объект
                        schedule_time = schedule['time']
                        
                    schedule_datetime = datetime.combine(schedule['date'], schedule_time)
                except Exception as e:
                    logger.error(f"Ошибка обработки времени для занятия {schedule['id']}: {e}, тип: {type(schedule['time'])}, значение: {schedule['time']}")
                    continue
                time_diff = schedule_datetime - now
                
                # Уникальный ключ для напоминания
                reminder_key = f"{schedule['id']}_{schedule['date']}_{schedule['time']}"
                
                # Проверяем напоминание за день
                if timedelta(hours=20) <= time_diff <= timedelta(hours=28):
                    day_key = f"{reminder_key}_day"
                    if day_key not in sent_reminders:
                        # Отправляем репетитору
                        if schedule['tutor_chat_id']:
                            tutor_tz = schedule.get('tutor_timezone', 'Europe/Saratov')
                            await send_reminder(application.bot, schedule['tutor_chat_id'], schedule, 'репетитор', 'day', tutor_tz)
                        # Отправляем ученику
                        if schedule['student_chat_id']:
                            student_tz = schedule.get('student_timezone', 'Europe/Saratov')
                            await send_reminder(application.bot, schedule['student_chat_id'], schedule, 'ученик', 'day', student_tz)
                        sent_reminders.add(day_key)
                
                # Проверяем напоминание за час
                elif timedelta(minutes=55) <= time_diff <= timedelta(minutes=65):
                    hour_key = f"{reminder_key}_hour"
                    if hour_key not in sent_reminders:
                        # Отправляем репетитору
                        if schedule['tutor_chat_id']:
                            tutor_tz = schedule.get('tutor_timezone', 'Europe/Saratov')
                            await send_reminder(application.bot, schedule['tutor_chat_id'], schedule, 'репетитор', 'hour', tutor_tz)
                        # Отправляем ученику
                        if schedule['student_chat_id']:
                            student_tz = schedule.get('student_timezone', 'Europe/Saratov')
                            await send_reminder(application.bot, schedule['student_chat_id'], schedule, 'ученик', 'hour', student_tz)
                        sent_reminders.add(hour_key)
                
                # Проверяем напоминание за 10 минут
                elif timedelta(minutes=8) <= time_diff <= timedelta(minutes=12):
                    ten_min_key = f"{reminder_key}_10min"
                    if ten_min_key not in sent_reminders:
                        # Отправляем репетитору
                        if schedule['tutor_chat_id']:
                            tutor_tz = schedule.get('tutor_timezone', 'Europe/Saratov')
                            await send_reminder(application.bot, schedule['tutor_chat_id'], schedule, 'репетитор', '10min', tutor_tz)
                        # Отправляем ученику
                        if schedule['student_chat_id']:
                            student_tz = schedule.get('student_timezone', 'Europe/Saratov')
                            await send_reminder(application.bot, schedule['student_chat_id'], schedule, 'ученик', '10min', student_tz)
                        sent_reminders.add(ten_min_key)
            
            # Очищаем старые записи
            if len(sent_reminders) > 1000:
                sent_reminders.clear()
            
            cursor.close()
            conn.close()
            
            await asyncio.sleep(60)  # Проверяем каждую минуту
            
        except Exception as e:
            logger.error(f"Ошибка при проверке расписания: {e}")
            await asyncio.sleep(60)

async def post_init(application: Application) -> None:
    """Запуск фоновых задач после инициализации бота"""
    # Запускаем задачу проверки расписания
    application.create_task(check_schedules(application))

def main():
    """Главная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик callback запросов (для выбора часового пояса)
    application.add_handler(CallbackQueryHandler(handle_timezone_callback, pattern="^tz:"))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()