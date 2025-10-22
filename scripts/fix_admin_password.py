#!/usr/bin/env python3
"""
Скрипт для сброса пароля администратора
"""
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def reset_admin_password(new_password='admin'):
    """Сбрасывает пароль администратора на указанный"""
    try:
        # Подключаемся к MySQL
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = conn.cursor()
        
        # Генерируем новый хеш пароля
        new_hash = generate_password_hash(new_password)
        
        # Проверяем существует ли пользователь admin
        cursor.execute("SELECT id FROM user WHERE username = 'admin'")
        admin_exists = cursor.fetchone()
        
        if admin_exists:
            # Обновляем пароль
            cursor.execute("""
                UPDATE user 
                SET password_hash = %s 
                WHERE username = 'admin'
            """, (new_hash,))
            print(f"✅ Пароль администратора обновлен на: {new_password}")
        else:
            # Создаем пользователя admin
            cursor.execute("""
                INSERT INTO user (username, password_hash)
                VALUES ('admin', %s)
            """, (new_hash,))
            print(f"✅ Создан пользователь admin с паролем: {new_password}")
        
        conn.commit()
        print(f"📝 Хеш пароля: {new_hash}")
        
    except mysql.connector.Error as err:
        print(f"❌ Ошибка: {err}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    password = sys.argv[1] if len(sys.argv) > 1 else 'admin'
    reset_admin_password(password)