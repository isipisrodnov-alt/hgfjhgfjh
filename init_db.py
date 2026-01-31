"""Инициализация базы данных для приложения Логист-Транс"""
import sqlite3
import hashlib
from datetime import datetime, timedelta

def hash_password(password):
    """Хеширование пароля SHA256"""
    salt = "LogisticTransSalt2026"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def init_database():
    """Создание таблиц и заполнение начальными данными"""
    conn = sqlite3.connect('logist_trans.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('Администратор', 'Логист', 'Водитель')),
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица клиентов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_info TEXT,
        email TEXT,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица заказов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        cargo_description TEXT,
        weight REAL CHECK (weight >= 0),
        address_from TEXT NOT NULL,
        address_to TEXT NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        planned_delivery_date DATE,
        actual_delivery_date DATE,
        cost REAL CHECK (cost >= 0),
        status TEXT NOT NULL DEFAULT 'Создан',
        created_by_id INTEGER,
        notes TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (created_by_id) REFERENCES users(id)
    )
    ''')
    
    # Таблица транспортных средств
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT,
        model TEXT,
        license_plate TEXT UNIQUE NOT NULL,
        capacity REAL CHECK (capacity > 0),
        status TEXT NOT NULL DEFAULT 'Свободен',
        last_maintenance_date DATE,
        next_maintenance_km INTEGER,
        current_mileage INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица водителей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        full_name TEXT NOT NULL,
        phone TEXT,
        license_number TEXT,
        experience_years INTEGER,
        is_available INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Таблица маршрутов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        driver_id INTEGER,
        vehicle_id INTEGER,
        start_point TEXT,
        end_point TEXT,
        planned_start_time TIMESTAMP,
        planned_end_time TIMESTAMP,
        actual_start_time TIMESTAMP,
        actual_end_time TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'Запланирован',
        distance_km REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (driver_id) REFERENCES drivers(id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
    )
    ''')
    
    # Таблица складских записей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warehouse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cargo_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        storage_zone TEXT,
        volume REAL,
        status TEXT DEFAULT 'На складе',
        arrival_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        departure_date TIMESTAMP,
        order_id INTEGER,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    )
    ''')
    
    # Таблица уведомлений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        type TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        order_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (order_id) REFERENCES orders(id)
    )
    ''')
    
    # Таблица истории статусов заказов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        changed_by_id INTEGER,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (changed_by_id) REFERENCES users(id)
    )
    ''')
    
    # Индексы для оптимизации
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_client ON orders(client_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_routes_order ON routes(order_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)')
    
    # Заполнение начальными данными
    # Пользователи
    users_data = [
        ('admin', hash_password('admin123'), 'Иванов А.С.', 'Администратор'),
        ('logist', hash_password('logist123'), 'Петрова Е.В.', 'Логист'),
        ('driver1', hash_password('driver123'), 'Сидоров П.К.', 'Водитель'),
    ]
    
    cursor.executemany(
        'INSERT OR IGNORE INTO users (login, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
        users_data
    )
    
    # Клиенты
    clients_data = [
        ('ООО "СтройМатериалы"', 'Москва, ул. Строителей, 1', 'info@stroymat.ru', '+74951112233'),
        ('ИП Кузнецов А.В.', 'Санкт-Петербург, пр. Невский, 45', 'kuznetsov@mail.ru', '+78127778899'),
        ('АО "ТехноЛогистика"', 'Екатеринбург, ул. Машиностроителей, 12', 'tech@logist.ru', '+73432223344'),
    ]
    
    cursor.executemany(
        'INSERT OR IGNORE INTO clients (name, contact_info, email, phone) VALUES (?, ?, ?, ?)',
        clients_data
    )
    
    # Транспортные средства
    vehicles_data = [
        ('Volvo', 'FH16', 'А123ВС77', 25.0, 'Свободен'),
        ('Mercedes', 'Actros', 'Б456ДЕ77', 20.5, 'В рейсе'),
        ('КАМАЗ', '6520', 'В789ЖЗ77', 18.0, 'На ремонте'),
    ]
    
    cursor.executemany(
        'INSERT OR IGNORE INTO vehicles (brand, model, license_plate, capacity, status) VALUES (?, ?, ?, ?, ?)',
        vehicles_data
    )
    
    # Водители
    cursor.execute('INSERT OR IGNORE INTO drivers (user_id, full_name, phone, license_number, experience_years, is_available) VALUES (?, ?, ?, ?, ?, ?)',
        (3, 'Сидоров П.К.', '+79001112233', 'АВ123456', 10, 1))
    
    # Заказы
    orders_data = [
        ('ORD-20260130-ABC123', 1, 'Цемент, мешки', 12.5, 'Москва, склад №1', 'Санкт-Петербург, ул. Заводская, 5', 
         datetime.now(), (datetime.now() + timedelta(days=2)).date(), None, 45000.0, 'В пути', 1, 'Срочный заказ'),
        ('ORD-20260130-DEF456', 2, 'Мебель офисная', 3.2, 'Екатеринбург, ул. Мебельная, 12', 'Новосибирск, пр. Ленина, 89',
         datetime.now(), (datetime.now() + timedelta(days=3)).date(), None, 28000.0, 'Создан', 2, None),
    ]
    
    cursor.executemany(
        '''INSERT OR IGNORE INTO orders 
        (order_number, client_id, cargo_description, weight, address_from, address_to, 
         order_date, planned_delivery_date, actual_delivery_date, cost, status, created_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        orders_data
    )
    
    # Маршруты
    cursor.execute('''INSERT OR IGNORE INTO routes 
    (order_id, driver_id, vehicle_id, start_point, end_point, status)
    VALUES (?, ?, ?, ?, ?, ?)''',
        (1, 1, 2, 'Москва, склад №1', 'Санкт-Петербург, ул. Заводская, 5', 'В пути'))
    
    # Склад
    warehouse_data = [
        ('Цемент', 500, 'Зона А', 25.5, 'Зарезервирован', datetime.now(), None, 1),
        ('Кирпич', 10000, 'Зона Б', 150.0, 'На складе', datetime.now(), None, None),
    ]
    
    cursor.executemany(
        '''INSERT OR IGNORE INTO warehouse 
        (cargo_name, quantity, storage_zone, volume, status, arrival_date, departure_date, order_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        warehouse_data
    )
    
    # Уведомления
    notifications_data = [
        (2, 'Новый заказ №1 от ООО "СтройМатериалы"', 'Новый заказ', 0, 1),
        (3, 'Вам назначен маршрут №1', 'Назначение маршрута', 0, 1),
    ]
    
    cursor.executemany(
        'INSERT OR IGNORE INTO notifications (user_id, message, type, is_read, order_id) VALUES (?, ?, ?, ?, ?)',
        notifications_data
    )
    
    conn.commit()
    conn.close()
    print("✓ База данных инициализирована успешно!")

if __name__ == '__main__':
    init_database()
