-- Инициализация базы данных для Docker контейнера
-- Версия без ENUM типов, с использованием VARCHAR

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Создание таблицы пользователей (для админки)
CREATE TABLE IF NOT EXISTS user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Создание таблицы Telegram пользователей (БЕЗ ENUM!)
CREATE TABLE IF NOT EXISTS telegram_id (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(200),
    status VARCHAR(50) NOT NULL, -- Просто VARCHAR вместо ENUM
    chat_id BIGINT,
    parent_id VARCHAR(100),
    additional_description TEXT,
    timezone VARCHAR(50) DEFAULT '+04:00' -- Часовой пояс пользователя (по умолчанию +4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Создание таблицы пар репетитор-ученик
CREATE TABLE IF NOT EXISTS pair (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tutor_id INT NOT NULL,
    student_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tutor_id) REFERENCES telegram_id(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES telegram_id(id) ON DELETE CASCADE,
    UNIQUE KEY unique_pair (tutor_id, student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Создание таблицы предметов
CREATE TABLE IF NOT EXISTS subject (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Создание таблицы расписания
CREATE TABLE IF NOT EXISTS schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tutor_id INT NOT NULL,
    student_id INT NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    subject_id INT NOT NULL,
    lesson_type VARCHAR(20) DEFAULT 'regular',
    duration_minutes INT DEFAULT 60,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tutor_id) REFERENCES telegram_id(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES telegram_id(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subject(id) ON DELETE CASCADE,
    INDEX idx_date (date),
    INDEX idx_tutor (tutor_id),
    INDEX idx_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Создание таблицы напоминаний (тоже БЕЗ ENUM!)
CREATE TABLE IF NOT EXISTS reminder (
    id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_id INT NOT NULL,
    reminder_type VARCHAR(20) NOT NULL DEFAULT 'day', -- Просто VARCHAR вместо ENUM
    sent BOOLEAN DEFAULT FALSE,
    sent_at DATETIME,
    last_sent DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES schedule(id) ON DELETE CASCADE,
    UNIQUE KEY unique_reminder (schedule_id, reminder_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Добавление примеров предметов (необязательно)
INSERT IGNORE INTO subject (name) VALUES 
    ('Математика'),
    ('Русский язык'),
    ('Английский язык'),
    ('Физика'),
    ('Химия'),
    ('Биология'),
    ('История'),
    ('Обществознание'),
    ('География'),
    ('Информатика');