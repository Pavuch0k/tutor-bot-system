import pytest
import os
import sys
from unittest.mock import Mock, patch

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, TelegramID, Schedule, Subject

@pytest.fixture
def client():
    """Фикстура для создания тестового клиента Flask"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def test_user():
    """Фикстура для создания тестового пользователя"""
    with app.app_context():
        user = User(username='testuser', password_hash='hashed_password')
        db.session.add(user)
        db.session.commit()
        return user

def test_index_redirect(client):
    """Тест редиректа с главной страницы"""
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.location

def test_login_page(client):
    """Тест страницы входа"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()

def test_login_invalid_credentials(client):
    """Тест входа с неверными данными"""
    response = client.post('/login', data={
        'username': 'nonexistent',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200

def test_login_valid_credentials(client, test_user):
    """Тест входа с верными данными"""
    with patch('flask_login.login_user'):
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'anypassword'
        }, follow_redirects=True)
        # Проверяем, что нет ошибки редиректа
        assert response.status_code == 200

def test_protected_route_without_login(client):
    """Тест доступа к защищенному маршруту без входа"""
    response = client.get('/admin/users')
    assert response.status_code == 302  # Редирект на страницу входа

def test_add_telegram_id_authenticated(client, test_user):
    """Тест добавления Telegram ID с аутентификацией"""
    with patch('flask_login.login_user'):
        with patch('flask_login.current_user', test_user):
            response = client.post('/add_telegram_id', data={
                'telegram_id': '@testuser',
                'description': 'Test User',
                'status': 'репетитор',
                'timezone': '+04:00'
            })
            # Проверяем ответ
            assert response.status_code == 302  # Редирект после успешного добавления

def test_add_subject_authenticated(client, test_user):
    """Тест добавления предмета с аутентификацией"""
    with patch('flask_login.login_user'):
        with patch('flask_login.current_user', test_user):
            response = client.post('/add_subject', data={
                'name': 'Test Subject'
            })
            # Проверяем ответ JSON
            assert response.status_code == 200

def test_model_creation():
    """Тест создания моделей данных"""
    with app.app_context():
        db.create_all()
        
        # Тест создания пользователя
        user = User(username='testuser', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        
        assert User.query.count() == 1
        assert user.username == 'testuser'
        
        # Тест создания Telegram ID
        telegram_id = TelegramID(
            telegram_id='@testuser',
            description='Test User',
            status='репетитор'
        )
        db.session.add(telegram_id)
        db.session.commit()
        
        assert TelegramID.query.count() == 1
        assert telegram_id.status == 'репетитор'
        
        # Тест создания предмета
        subject = Subject(name='Mathematics')
        db.session.add(subject)
        db.session.commit()
        
        assert Subject.query.count() == 1
        assert subject.name == 'Mathematics'

def test_schedule_model_creation():
    """Тест создания модели расписания"""
    with app.app_context():
        db.create_all()
        
        # Создаем тестовые данные
        tutor = TelegramID(
            telegram_id='@tutor',
            description='Tutor',
            status='репетитор'
        )
        student = TelegramID(
            telegram_id='@student',
            description='Student',
            status='ученик'
        )
        subject = Subject(name='Mathematics')
        
        db.session.add_all([tutor, student, subject])
        db.session.commit()
        
        # Создаем расписание
        from datetime import date, time
        schedule = Schedule(
            tutor_id=tutor.id,
            student_id=student.id,
            date=date.today(),
            time=time(10, 0),
            subject_id=subject.id
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        assert Schedule.query.count() == 1
        assert schedule.tutor_id == tutor.id
        assert schedule.student_id == student.id
        assert schedule.subject_id == subject.id

if __name__ == '__main__':
    pytest.main([__file__])