from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import pytz
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Добавляем функцию для сериализации datetime
def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    if isinstance(x, timedelta):
        return str(x)
    raise TypeError(f"Object of type {type(x)} is not JSON serializable")

app.json_encoder = type('JSONEncoder', (json.JSONEncoder,), {'default': datetime_handler})

# Часовой пояс системы (Саратов)
SYSTEM_TIMEZONE = pytz.timezone('Europe/Saratov')  # UTC+4

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
        app.logger.error(f"Ошибка конвертации времени: {e}")
        return system_datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class TelegramID(db.Model):
    __tablename__ = 'telegram_id'
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(200))
    status = db.Column(db.String(50), nullable=False)  # Просто строка вместо Enum
    chat_id = db.Column(db.BigInteger)
    parent_id = db.Column(db.String(100))  # ID родителя для учеников
    additional_description = db.Column(db.Text)  # Дополнительное описание
    timezone = db.Column(db.String(50), default='+04:00')  # Часовой пояс пользователя
    student_notify_day = db.Column(db.Boolean, default=True)
    student_notify_hour = db.Column(db.Boolean, default=True)
    student_notify_10min = db.Column(db.Boolean, default=True)
    parent_notify_day = db.Column(db.Boolean, default=True)
    parent_notify_hour = db.Column(db.Boolean, default=True)
    parent_notify_10min = db.Column(db.Boolean, default=True)

class Pair(db.Model):
    __tablename__ = 'pair'
    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('telegram_id.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('telegram_id.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения для пользователей
    tutor = db.relationship('TelegramID', foreign_keys=[tutor_id], backref='tutor_pairs')
    student = db.relationship('TelegramID', foreign_keys=[student_id], backref='student_pairs')

class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('telegram_id.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('telegram_id.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id', ondelete='CASCADE'), nullable=False)
    lesson_type = db.Column(db.String(20), default='regular')  # 'regular' или 'trial'
    duration_minutes = db.Column(db.Integer, default=60)  # Продолжительность в минутах
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения
    tutor = db.relationship('TelegramID', foreign_keys=[tutor_id], backref='tutor_schedules')
    student = db.relationship('TelegramID', foreign_keys=[student_id], backref='student_schedules')
    subject = db.relationship('Subject', backref='schedules')
    
    # Отношение для напоминаний с каскадным удалением
    reminders = db.relationship('Reminder', backref='schedule', lazy=True, cascade='all, delete-orphan')

class Reminder(db.Model):
    __tablename__ = 'reminder'
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id', ondelete='CASCADE'), nullable=False)
    reminder_type = db.Column(db.String(20), nullable=False)  # Просто строка вместо Enum
    sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    last_sent = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
        flash('Неверные учетные данные')
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin():
    # Редирект на страницу пользователей по умолчанию
    return redirect(url_for('admin_users'))

@app.route('/admin/users')
@login_required
def admin_users():
    telegram_ids = TelegramID.query.all()
    return render_template('users.html', telegram_ids=telegram_ids)

@app.route('/admin/pairs')
@login_required
def admin_pairs():
    telegram_ids = TelegramID.query.all()
    # Получаем пары с данными репетиторов и учеников
    pairs = db.session.query(
        Pair,
        TelegramID.description.label('tutor_name'),
        TelegramID.telegram_id.label('tutor_telegram')
    ).join(
        TelegramID, Pair.tutor_id == TelegramID.id
    ).all()
    
    # Дополнительно получаем данные учеников для каждой пары
    for pair_data in pairs:
        pair, tutor_name, tutor_telegram = pair_data
        student = TelegramID.query.get(pair.student_id)
        pair.student_name = student.description if student else 'Неизвестно'
        pair.student_telegram = student.telegram_id if student else 'Неизвестно'
        pair.tutor_name = tutor_name
        pair.tutor_telegram = tutor_telegram
    
    return render_template('pairs.html', telegram_ids=telegram_ids, pairs=[p[0] for p in pairs])

@app.route('/admin/schedule')
@login_required
def admin_schedule():
    tutors = TelegramID.query.filter_by(status='репетитор').all()
    students = TelegramID.query.filter_by(status='ученик').all()
    subjects = Subject.query.all()
    return render_template('schedule_admin.html', tutors=tutors, students=students, subjects=subjects)

@app.route('/admin/settings')
@login_required
def admin_settings():
    return render_template('settings.html')

@app.route('/admin/subjects')
@login_required
def admin_subjects():
    subjects = Subject.query.all()
    return render_template('subjects.html', subjects=subjects)

@app.route('/admin/tests')
@login_required
def admin_tests():
    tutors = TelegramID.query.filter_by(status='репетитор').all()
    students = TelegramID.query.filter_by(status='ученик').all()
    subjects = Subject.query.all()
    return render_template('tests.html', tutors=tutors, students=students, subjects=subjects)

@app.route('/api/run_report_test', methods=['POST'])
@login_required
def run_report_test():
    """Запуск теста системы отчётов"""
    try:
        tutor_id = request.json.get('tutor_id')
        student_id = request.json.get('student_id')
        subject_id = request.json.get('subject_id')
        test_date_str = request.json.get('date')
        test_time_str = request.json.get('time')
        
        if not all([tutor_id, student_id, subject_id]):
            return jsonify({'success': False, 'error': 'Выберите репетитора, ученика и предмет'})
        
        # Проверяем, что пользователи существуют
        tutor = TelegramID.query.get(tutor_id)
        student = TelegramID.query.get(student_id)
        subject = Subject.query.get(subject_id)
        
        if not tutor or not student or not subject:
            return jsonify({'success': False, 'error': 'Репетитор, ученик или предмет не найдены'})
        
        # Обрабатываем дату и время
        if test_date_str and test_time_str:
            # Используем указанные дату и время (время в часовом поясе Саратова)
            test_date = datetime.strptime(test_date_str, '%Y-%m-%d').date()
            test_time = datetime.strptime(test_time_str, '%H:%M').time().replace(second=0, microsecond=0)
        else:
            # Fallback: создаем тестовое занятие на 2 минуты вперёд
            now = datetime.now(SYSTEM_TIMEZONE)
            test_date = now.date()
            test_time = (now + timedelta(minutes=2)).time().replace(second=0, microsecond=0)
        
        # Создаем занятие с длительностью 2 минуты
        test_schedule = Schedule(
            tutor_id=tutor_id,
            student_id=student_id,
            date=test_date,
            time=test_time,
            subject_id=subject_id,
            lesson_type='regular',
            duration_minutes=2
        )
        
        db.session.add(test_schedule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Тестовое занятие создано на {test_date.strftime("%d.%m.%Y")} в {test_time.strftime("%H:%M")} (Саратов UTC+4). Через 3 минуты после завершения репетитору придёт напоминание об отчёте.',
            'schedule_id': test_schedule.id
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Ошибка при создании тестового занятия: {e}')
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_telegram_id', methods=['POST'])
@login_required
def add_telegram_id():
    telegram_id = request.form.get('telegram_id')
    description = request.form.get('description')
    status = request.form.get('status')
    parent_id = request.form.get('parent_id') if request.form.get('status') == 'ученик' else None
    additional_description = request.form.get('additional_description')
    timezone = request.form.get('timezone', '+04:00')
    
    # Убираем @ и лишние кавычки если они есть в telegram_id
    if telegram_id:
        telegram_id = telegram_id.strip().lstrip('@').strip("'\"") 
    
    # Убираем @ и лишние кавычки если они есть в parent_id
    if parent_id is not None:  # Проверяем даже пустые строки
        parent_id = parent_id.strip().lstrip('@').strip("'\"")
    # Если parent_id пустой или None, делаем его None
    if not parent_id:
        parent_id = None
    
    # Очищаем и проверяем status
    if status:
        status = status.strip().strip("'\"")
        
    if telegram_id and status:
        # Проверяем, что status имеет допустимое значение
        if status not in ['репетитор', 'ученик']:
            flash(f'Недопустимый статус: {status}. Используйте "репетитор" или "ученик"')
            app.logger.error(f'Invalid status value: {repr(status)}')
            return redirect(url_for('admin_users'))
            
        try:
            # Создаем новую запись без chat_id (он будет NULL)
            new_id = TelegramID()
            new_id.telegram_id = telegram_id
            new_id.description = description
            new_id.status = status
            new_id.parent_id = parent_id
            new_id.additional_description = additional_description
            new_id.timezone = timezone
            # Настройки напоминаний
            new_id.student_notify_day = request.form.get('student_notify_day') == 'true'
            new_id.student_notify_hour = request.form.get('student_notify_hour') == 'true'
            new_id.student_notify_10min = request.form.get('student_notify_10min') == 'true'
            new_id.parent_notify_day = request.form.get('parent_notify_day') == 'true'
            new_id.parent_notify_hour = request.form.get('parent_notify_hour') == 'true'
            new_id.parent_notify_10min = request.form.get('parent_notify_10min') == 'true'
            # chat_id не устанавливаем - будет NULL
            
            db.session.add(new_id)
            db.session.commit()
            flash('ID успешно добавлен')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении: {str(e)}')
            app.logger.error(f'Error adding telegram_id: {e}')
    return redirect(url_for('admin_users'))

@app.route('/edit_telegram_id/<int:id>', methods=['POST'])
@login_required
def edit_telegram_id(id):
    telegram_id_obj = TelegramID.query.get_or_404(id)
    
    # Получаем новые значения из формы
    new_telegram_id = request.form.get('telegram_id')
    new_parent_id = request.form.get('parent_id') if request.form.get('status') == 'ученик' else None
    
    # Убираем @ и лишние кавычки если они есть
    if new_telegram_id:
        new_telegram_id = new_telegram_id.strip().lstrip('@').strip("'\"")
    if new_parent_id is not None:  # Проверяем даже пустые строки
        new_parent_id = new_parent_id.strip().lstrip('@').strip("'\"")
    # Если parent_id пустой или None, делаем его None
    if not new_parent_id:
        new_parent_id = None
    
    # Обновляем поля
    telegram_id_obj.telegram_id = new_telegram_id
    telegram_id_obj.description = request.form.get('description')
    telegram_id_obj.status = request.form.get('status')
    telegram_id_obj.parent_id = new_parent_id
    telegram_id_obj.additional_description = request.form.get('additional_description')
    
    # Обновляем настройки напоминаний (только для учеников)
    if request.form.get('status') == 'ученик':
        telegram_id_obj.student_notify_day = request.form.get('student_notify_day') == 'true'
        telegram_id_obj.student_notify_hour = request.form.get('student_notify_hour') == 'true'
        telegram_id_obj.student_notify_10min = request.form.get('student_notify_10min') == 'true'
        telegram_id_obj.parent_notify_day = request.form.get('parent_notify_day') == 'true'
        telegram_id_obj.parent_notify_hour = request.form.get('parent_notify_hour') == 'true'
        telegram_id_obj.parent_notify_10min = request.form.get('parent_notify_10min') == 'true'
    
    db.session.commit()
    flash('Запись успешно обновлена')
    return redirect(url_for('admin_users'))

@app.route('/delete_telegram_id/<int:id>')
@login_required
def delete_telegram_id(id):
    telegram_id = TelegramID.query.get_or_404(id)
    
    # Сначала удаляем все связанные записи из расписания
    Schedule.query.filter(
        (Schedule.tutor_id == id) | (Schedule.student_id == id)
    ).delete()
    
    # Удаляем все пары, где этот пользователь участвует
    Pair.query.filter(
        (Pair.tutor_id == id) | (Pair.student_id == id)
    ).delete()
    
    # Теперь можно безопасно удалить самого пользователя
    db.session.delete(telegram_id)
    db.session.commit()
    
    flash('Пользователь и все связанные записи успешно удалены')
    return redirect(url_for('admin_users'))

@app.route('/add_pair', methods=['POST'])
@login_required
def add_pair():
    tutor_id = request.form.get('tutor_id')
    student_id = request.form.get('student_id')
    
    if tutor_id and student_id:
        try:
            new_pair = Pair(
                tutor_id=tutor_id,
                student_id=student_id
            )
            db.session.add(new_pair)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Пара успешно создана'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Ошибка при создании пары: {str(e)}'})
    else:
        return jsonify({'success': False, 'error': 'Пожалуйста, выберите репетитора и ученика'})

@app.route('/delete_pair/<int:id>')
@login_required
def delete_pair(id):
    pair = Pair.query.get_or_404(id)
    
    # Удаляем все записи из расписания для этой пары
    schedules_to_delete = Schedule.query.filter_by(
        tutor_id=pair.tutor_id,
        student_id=pair.student_id
    ).all()
    
    for schedule in schedules_to_delete:
        db.session.delete(schedule)
    
    # Удаляем саму пару
    db.session.delete(pair)
    db.session.commit()
    
    schedules_count = len(schedules_to_delete)
    if schedules_count > 0:
        flash(f'Пара успешно удалена вместе с {schedules_count} записями в расписании')
    else:
        flash('Пара успешно удалена')
    
    return redirect(url_for('admin_pairs'))

@app.route('/add_schedule', methods=['POST'])
@login_required
def add_schedule():
    tutor_id = request.form.get('tutor_id')
    student_id = request.form.get('student_id')
    date = request.form.get('date')
    time = request.form.get('time')
    subject_id = request.form.get('subject_id')
    repeat_count = request.form.get('repeat_count')
    lesson_type = request.form.get('lesson_type', 'regular')  # Получаем тип занятия
    is_trial = request.form.get('is_trial') == 'true'  # Чекбокс пробного занятия
    
    if not all([tutor_id, student_id, date, time, subject_id]):
        return jsonify({'success': False, 'error': 'Пожалуйста, заполните все поля'})
    
    try:
        # Проверяем, существуют ли пользователи
        tutor = TelegramID.query.get(tutor_id)
        student = TelegramID.query.get(student_id)
        if not tutor or not student:
            return jsonify({'success': False, 'error': 'Репетитор или ученик не найдены'})
        
        # Преобразуем строку даты в объект date
        lesson_date = datetime.strptime(date, '%Y-%m-%d').date()
        lesson_time = datetime.strptime(time, '%H:%M').time()
        
        # Определяем тип занятия и продолжительность
        final_lesson_type = 'trial' if is_trial else lesson_type
        duration = 30 if final_lesson_type == 'trial' else 60  # Пробное - 30 минут, обычное - 60
        
        # Определяем количество повторений
        weeks_to_repeat = 1
        if repeat_count and repeat_count.strip():
            try:
                weeks_to_repeat = int(repeat_count)
                weeks_to_repeat = max(1, min(weeks_to_repeat, 52))  # Ограничиваем от 1 до 52 недель
            except ValueError:
                weeks_to_repeat = 1
        
        created_count = 0
        skipped_count = 0
        
        # Создаем занятия на указанное количество недель
        for week in range(weeks_to_repeat):
            current_date = lesson_date + timedelta(weeks=week)
            
            # Проверяем, нет ли уже занятия в это время
            existing_schedule = Schedule.query.filter_by(
                tutor_id=tutor_id,
                student_id=student_id,
                date=current_date,
                time=lesson_time
            ).first()
            
            if not existing_schedule:
                new_schedule = Schedule(
                    tutor_id=tutor_id,
                    student_id=student_id,
                    date=current_date,
                    time=lesson_time,
                    subject_id=subject_id,
                    lesson_type=final_lesson_type,
                    duration_minutes=duration
                )
                db.session.add(new_schedule)
                created_count += 1
            else:
                skipped_count += 1
        
        db.session.commit()
        
        if weeks_to_repeat > 1:
            message = f'Создано {created_count} занятий'
            if skipped_count > 0:
                message += f' (пропущено {skipped_count} - уже существуют)'
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': True})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/edit_schedule/<int:id>', methods=['POST'])
@login_required
def edit_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    date = request.form.get('date')
    time = request.form.get('time')
    subject_id = request.form.get('subject_id')
    is_trial = request.form.get('is_trial') == 'true'
    
    if not all([date, time, subject_id]):
        return jsonify({'success': False, 'error': 'Пожалуйста, заполните все поля'})
    
    try:
        lesson_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Проверяем, нет ли уже занятия в это время
        existing_schedule = Schedule.query.filter(
            Schedule.tutor_id == schedule.tutor_id,
            Schedule.student_id == schedule.student_id,
            Schedule.date == lesson_date,
            Schedule.time == datetime.strptime(time, '%H:%M').time(),
            Schedule.id != schedule.id
        ).first()
        
        if existing_schedule:
            return jsonify({'success': False, 'error': 'Занятие в это время уже существует'})
        
        # Обновляем тип занятия и продолжительность
        final_lesson_type = 'trial' if is_trial else 'regular'
        duration = 30 if final_lesson_type == 'trial' else 60
        
        schedule.date = lesson_date
        schedule.time = datetime.strptime(time, '%H:%M').time()
        schedule.subject_id = subject_id
        schedule.lesson_type = final_lesson_type
        schedule.duration_minutes = duration
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/update_schedule/<int:id>', methods=['POST'])
@login_required
def update_schedule(id):
    try:
        schedule = Schedule.query.get_or_404(id)
        
        # Получаем новые данные из формы
        tutor_id = request.form.get('tutor_id')
        student_id = request.form.get('student_id')
        date = request.form.get('date')
        time = request.form.get('time')
        subject_id = request.form.get('subject_id')
        
        if not all([tutor_id, student_id, date, time, subject_id]):
            return jsonify({'success': False, 'error': 'Пожалуйста, заполните все поля'})
        
        # Преобразуем дату
        lesson_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Проверяем, нет ли конфликта с другим занятием (кроме текущего)
        existing_schedule = Schedule.query.filter(
            Schedule.id != id,
            Schedule.tutor_id == tutor_id,
            Schedule.date == lesson_date,
            Schedule.time == time
        ).first()
        
        if existing_schedule:
            return jsonify({'success': False, 'error': 'У репетитора уже есть занятие в это время'})
        
        # Обновляем занятие
        schedule.tutor_id = tutor_id
        schedule.student_id = student_id
        schedule.date = lesson_date
        schedule.time = time
        schedule.subject_id = subject_id
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Занятие успешно обновлено'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_schedule/<int:id>')
@login_required
def delete_schedule(id):
    try:
        schedule = Schedule.query.get_or_404(id)
        db.session.delete(schedule)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/schedule')
def schedule():
    username = request.args.get('username')
    if not username:
        return "Пользователь не найден", 404
    
    user = TelegramID.query.filter_by(telegram_id=username).first()
    if not user:
        return "Пользователь не найден", 404
    
    # Получаем часовой пояс пользователя
    user_timezone_str = user.timezone if user.timezone else 'Europe/Saratov'
    
    # Находим все расписания где пользователь является репетитором или учеником
    if user.status == 'репетитор':
        user_schedules = Schedule.query.filter_by(tutor_id=user.id).all()
    else:
        user_schedules = Schedule.query.filter_by(student_id=user.id).all()
    
    # Формируем список расписаний
    schedules = []
    today = datetime.now().date()
    
    for schedule in user_schedules:
        # Создаем datetime объект в системном времени
        system_datetime = datetime.combine(schedule.date, schedule.time)
        
        # Конвертируем в пользовательский часовой пояс
        user_datetime = convert_time_to_user_timezone(system_datetime, user_timezone_str)
        
        schedules.append({
            'subject': schedule.subject.name,
            'time': user_datetime.strftime('%H:%M'),
            'date': user_datetime.strftime('%d.%m.%Y'),
            'tutor': schedule.tutor.description,
            'student': schedule.student.description,
            'is_past': schedule.date < today,  # Помечаем прошедшие занятия
            'system_date': schedule.date.strftime('%d.%m.%Y'),  # Системная дата для сортировки
            'system_time': schedule.time.strftime('%H:%M'),  # Системное время для сортировки
            'lesson_type': schedule.lesson_type if hasattr(schedule, 'lesson_type') else 'regular',  # Тип занятия
            'duration_minutes': schedule.duration_minutes if hasattr(schedule, 'duration_minutes') else 60  # Продолжительность
        })
    
    # Сортируем расписания по системной дате и времени (для корректной сортировки)
    schedules.sort(key=lambda x: (datetime.strptime(x['system_date'], '%d.%m.%Y'), x['system_time']))
    
    return render_template('schedule_view.html', schedules=schedules, user=user, user_timezone=user_timezone_str)

@app.route('/get_month_schedule')
@login_required
def get_month_schedule():
    month = int(request.args.get('month'))
    year = int(request.args.get('year'))
    selected_date = request.args.get('date')  # Опционально для фильтрации по дню
    
    if not all([month, year]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    # Получаем все занятия в указанном месяце
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    
    query = Schedule.query.filter(
        Schedule.date >= start_date,
        Schedule.date < end_date
    )
    
    # Если указана конкретная дата, фильтруем по ней
    if selected_date:
        query = query.filter(Schedule.date == datetime.strptime(selected_date, '%Y-%m-%d').date())
    
    schedules = query.order_by(Schedule.date, Schedule.time).all()
    
    month_schedule = []
    for schedule in schedules:
        month_schedule.append({
            'id': schedule.id,
            'date': schedule.date.strftime('%Y-%m-%d'),
            'time': schedule.time.strftime('%H:%M'),
            'subject': schedule.subject.name,
            'tutor_name': schedule.tutor.description,
            'student_name': schedule.student.description,
            'tutor_id': schedule.tutor_id,
            'student_id': schedule.student_id,
            'subject_id': schedule.subject_id,
            'lesson_type': schedule.lesson_type if hasattr(schedule, 'lesson_type') else 'regular',
            'duration_minutes': schedule.duration_minutes if hasattr(schedule, 'duration_minutes') else 60
        })
    
    return jsonify(month_schedule)

@app.route('/send_reminders')
def send_reminders():
    now = datetime.now()
    schedules = Schedule.query.all()
    
    for schedule in schedules:
        # Проверяем, нужно ли отправить напоминание
        reminder = Reminder.query.filter_by(schedule_id=schedule.id, reminder_type='hour').first()
        if not reminder or (reminder.last_sent and (now - reminder.last_sent).total_seconds() >= 60):
            # Здесь будет логика отправки напоминания через Telegram
            if reminder:
                reminder.last_sent = now
                reminder.sent = True
                reminder.sent_at = now
            else:
                reminder = Reminder(
                    schedule_id=schedule.id, 
                    reminder_type='hour',
                    last_sent=now,
                    sent=True,
                    sent_at=now
                )
                db.session.add(reminder)
            db.session.commit()
    
    return 'OK'

@app.route('/api/tutor_students/<int:tutor_id>')
@login_required
def get_tutor_students(tutor_id):
    # Получаем всех учеников, связанных с репетитором через таблицу Pair
    pairs = Pair.query.filter_by(tutor_id=tutor_id).all()
    students = []
    for pair in pairs:
        student = TelegramID.query.get(pair.student_id)
        if student:
            students.append({
                'id': student.id,
                'description': student.description,
                'telegram_id': student.telegram_id
            })
    return jsonify(students)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Проверяем текущий пароль
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Неверный текущий пароль')
        return redirect(url_for('admin'))
    
    # Проверяем совпадение новых паролей
    if new_password != confirm_password:
        flash('Новые пароли не совпадают')
        return redirect(url_for('admin'))
    
    # Проверяем длину нового пароля
    if len(new_password) < 6:
        flash('Новый пароль должен содержать минимум 6 символов')
        return redirect(url_for('admin'))
    
    # Обновляем пароль
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Пароль успешно изменен')
    return redirect(url_for('admin'))

@app.route('/add_subject', methods=['POST'])
@login_required
def add_subject():
    name = request.form.get('name')
    
    if not name:
        return jsonify({'success': False, 'error': 'Название предмета обязательно'})
    
    try:
        # Проверяем, существует ли уже предмет с таким названием
        existing_subject = Subject.query.filter_by(name=name).first()
        if existing_subject:
            return jsonify({'success': False, 'error': 'Предмет с таким названием уже существует'})
        
        new_subject = Subject(name=name)
        db.session.add(new_subject)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Предмет успешно добавлен'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Ошибка при добавлении предмета: {str(e)}'})

@app.route('/edit_subject/<int:id>', methods=['POST'])
@login_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)
    name = request.form.get('name')
    
    if not name:
        flash('Название предмета обязательно')
        return redirect(url_for('admin_subjects'))
    
    try:
        # Проверяем, существует ли уже предмет с таким названием
        existing_subject = Subject.query.filter(Subject.name == name, Subject.id != id).first()
        if existing_subject:
            flash('Предмет с таким названием уже существует')
            return redirect(url_for('admin_subjects'))
        
        subject.name = name
        db.session.commit()
        flash('Предмет успешно обновлен')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении предмета: {str(e)}')
    
    return redirect(url_for('admin_subjects'))

@app.route('/delete_subject/<int:id>')
@login_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    
    try:
        db.session.delete(subject)
        db.session.commit()
        flash('Предмет успешно удален')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении предмета: {str(e)}')
    
    return redirect(url_for('admin_subjects'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Создаем администратора, если его нет
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin')
            )
            db.session.add(admin)
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True) 