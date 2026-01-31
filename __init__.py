"""Инициализация приложения Flask"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os

db = SQLAlchemy()

def create_app():
    """Фабрика приложения Flask"""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Конфигурация
    app.config['SECRET_KEY'] = 'logist-trans-secret-key-2026'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///logist_trans.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Инициализация БД
    db.init_app(app)
    
    # Регистрация blueprints
    from app.routes import auth_bp, admin_bp, logistic_bp, driver_bp, api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(logistic_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(api_bp)
    
    return app
