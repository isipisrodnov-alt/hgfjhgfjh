"""Точка входа приложения Логист-Транс"""
import os
import sys
from init_db import init_database

# Инициализация БД если её нет
if not os.path.exists('logist_trans.db'):
    print("Инициализация базы данных...")
    init_database()

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  Приложение 'Логист-Транс' запущено!")
    print("="*60)
    print("\nТестовые учетные данные:")
    print("  Администратор: admin / admin123")
    print("  Логист:        logist / logist123")
    print("  Водитель:      driver1 / driver123")
    print("\nПриложение доступно по адресу: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
