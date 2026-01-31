"""Маршруты приложения Логист-Транс"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import hashlib
from datetime import datetime, timedelta
from functools import wraps
import uuid

# Blueprints
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logistic_bp = Blueprint('logistic', __name__, url_prefix='/logistic')
driver_bp = Blueprint('driver', __name__, url_prefix='/driver')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Вспомогательные функции
def get_db():
    """Получить подключение к БД"""
    conn = sqlite3.connect('logist_trans.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Хеширование пароля"""
    salt = "LogisticTransSalt2026"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Декоратор для проверки роли"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Пожалуйста, войдите в систему', 'warning')
                return redirect(url_for('auth.login'))
            
            db = get_db()
            user = db.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            db.close()
            
            if not user or user['role'] not in roles:
                flash('У вас нет доступа к этой странице', 'danger')
                return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============ АУТЕНТИФИКАЦИЯ ============
@auth_bp.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        db.close()
        
        if user['role'] == 'Администратор':
            return redirect(url_for('admin.dashboard'))
        elif user['role'] == 'Логист':
            return redirect(url_for('logistic.dashboard'))
        else:
            return redirect(url_for('driver.dashboard'))
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Введите логин и пароль', 'danger')
            return redirect(url_for('auth.login'))
        
        db = get_db()
        user = db.execute(
            'SELECT id, login, full_name, role, is_active FROM users WHERE login = ? AND password_hash = ?',
            (username, hash_password(password))
        ).fetchone()
        db.close()
        
        if user and user['is_active']:
            session['user_id'] = user['id']
            session['username'] = user['login']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            
            flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
            
            # Перенаправление по ролям
            if user['role'] == 'Администратор':
                return redirect(url_for('admin.dashboard'))
            elif user['role'] == 'Логист':
                return redirect(url_for('logistic.dashboard'))
            else:
                return redirect(url_for('driver.dashboard'))
        else:
            flash('Неверный логин или пароль', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))

# ============ АДМИНИСТРАТОР ============
@admin_bp.route('/dashboard')
@role_required('Администратор')
def dashboard():
    """Панель управления администратора"""
    db = get_db()
    
    stats = {
        'total_users': db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count'],
        'total_orders': db.execute('SELECT COUNT(*) as count FROM orders').fetchone()['count'],
        'total_vehicles': db.execute('SELECT COUNT(*) as count FROM vehicles').fetchone()['count'],
        'active_routes': db.execute("SELECT COUNT(*) as count FROM routes WHERE status = 'В пути'").fetchone()['count'],
    }
    
    recent_orders = db.execute('''
        SELECT o.id, o.order_number, c.name, o.status, o.cost, o.order_date
        FROM orders o
        JOIN clients c ON o.client_id = c.id
        ORDER BY o.order_date DESC LIMIT 10
    ''').fetchall()
    
    db.close()
    
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)

@admin_bp.route('/users')
@role_required('Администратор')
def users():
    """Управление пользователями"""
    db = get_db()
    users_list = db.execute('SELECT id, login, full_name, role, is_active, created_at FROM users').fetchall()
    db.close()
    
    return render_template('admin/users.html', users=users_list)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@role_required('Администратор')
def add_user():
    """Добавление пользователя"""
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (login, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                (login, hash_password(password), full_name, role)
            )
            db.commit()
            flash(f'Пользователь {login} добавлен', 'success')
            return redirect(url_for('admin.users'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким логином уже существует', 'danger')
        finally:
            db.close()
    
    return render_template('admin/add_user.html')

@admin_bp.route('/reports')
@role_required('Администратор')
def reports():
    """Аналитические отчеты"""
    db = get_db()
    
    # Статистика по статусам заказов
    order_stats = db.execute('''
        SELECT status, COUNT(*) as count, SUM(cost) as total_cost
        FROM orders
        GROUP BY status
    ''').fetchall()
    
    # Статистика по транспорту
    vehicle_stats = db.execute('''
        SELECT status, COUNT(*) as count
        FROM vehicles
        GROUP BY status
    ''').fetchall()
    
    db.close()
    
    return render_template('admin/reports.html', order_stats=order_stats, vehicle_stats=vehicle_stats)

# ============ ЛОГИСТ ============
@logistic_bp.route('/dashboard')
@role_required('Логист', 'Администратор')
def dashboard():
    """Панель логиста"""
    db = get_db()
    
    user_id = session['user_id']
    
    stats = {
        'active_orders': db.execute("SELECT COUNT(*) as count FROM orders WHERE status IN ('В пути', 'Назначен')").fetchone()['count'],
        'pending_orders': db.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'Создан'").fetchone()['count'],
        'available_vehicles': db.execute("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Свободен'").fetchone()['count'],
        'unread_notifications': db.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,)).fetchone()['count'],
    }
    
    recent_orders = db.execute('''
        SELECT o.id, o.order_number, c.name, o.status, o.cost, o.planned_delivery_date
        FROM orders o
        JOIN clients c ON o.client_id = c.id
        ORDER BY o.order_date DESC LIMIT 10
    ''').fetchall()
    
    db.close()
    
    return render_template('logistic/dashboard.html', stats=stats, recent_orders=recent_orders)

@logistic_bp.route('/orders')
@role_required('Логист', 'Администратор')
def orders():
    """Список заказов"""
    db = get_db()
    
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = '''
        SELECT o.id, o.order_number, c.name, o.status, o.cost, o.weight, 
               o.planned_delivery_date, o.order_date
        FROM orders o
        JOIN clients c ON o.client_id = c.id
        WHERE 1=1
    '''
    params = []
    
    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    if search:
        query += ' AND (o.order_number LIKE ? OR c.name LIKE ? OR o.cargo_description LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    query += ' ORDER BY o.order_date DESC'
    
    orders_list = db.execute(query, params).fetchall()
    statuses = db.execute('SELECT DISTINCT status FROM orders').fetchall()
    
    db.close()
    
    return render_template('logistic/orders.html', orders=orders_list, statuses=statuses, current_status=status_filter, search=search)

@logistic_bp.route('/orders/create', methods=['GET', 'POST'])
@role_required('Логист', 'Администратор')
def create_order():
    """Создание заказа"""
    db = get_db()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        cargo_description = request.form.get('cargo_description')
        weight = request.form.get('weight')
        address_from = request.form.get('address_from')
        address_to = request.form.get('address_to')
        planned_delivery_date = request.form.get('planned_delivery_date')
        cost = request.form.get('cost')
        notes = request.form.get('notes')
        vehicle_id = request.form.get('vehicle_id')
        driver_id = request.form.get('driver_id')
        
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        
        try:
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO orders 
                (order_number, client_id, cargo_description, weight, address_from, address_to,
                 planned_delivery_date, cost, status, created_by_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_number, client_id, cargo_description, weight, address_from, address_to,
                  planned_delivery_date, cost, 'Создан', session['user_id'], notes))
            
            order_id = cursor.lastrowid
            
            # Создание маршрута, если указан транспорт
            if vehicle_id and driver_id:
                cursor.execute('''
                    INSERT INTO routes (order_id, driver_id, vehicle_id, start_point, end_point, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, driver_id, vehicle_id, address_from, address_to, 'Запланирован'))
                
                # Обновление статуса транспорта и водителя
                cursor.execute('UPDATE vehicles SET status = ? WHERE id = ?', ('Назначен', vehicle_id))
                cursor.execute('UPDATE drivers SET is_available = ? WHERE id = ?', (0, driver_id))
                cursor.execute('UPDATE orders SET status = ? WHERE id = ?', ('Назначен', order_id))
            
            # Запись в историю
            cursor.execute('''
                INSERT INTO order_status_history (order_id, new_status, changed_by_id, notes)
                VALUES (?, ?, ?, ?)
            ''', (order_id, 'Создан', session['user_id'], 'Заказ создан'))
            
            db.commit()
            flash(f'Заказ {order_number} успешно создан', 'success')
            return redirect(url_for('logistic.orders'))
        
        except Exception as e:
            db.rollback()
            flash(f'Ошибка создания заказа: {str(e)}', 'danger')
    
    clients = db.execute('SELECT id, name FROM clients ORDER BY name').fetchall()
    vehicles = db.execute("SELECT id, brand, model, license_plate FROM vehicles WHERE status = 'Свободен'").fetchall()
    drivers = db.execute('SELECT id, full_name FROM drivers WHERE is_available = 1').fetchall()
    
    db.close()
    
    return render_template('logistic/create_order.html', clients=clients, vehicles=vehicles, drivers=drivers)

@logistic_bp.route('/orders/<int:order_id>/edit', methods=['GET', 'POST'])
@role_required('Логист', 'Администратор')
def edit_order(order_id):
    """Редактирование заказа"""
    db = get_db()
    
    order = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order:
        flash('Заказ не найден', 'danger')
        return redirect(url_for('logistic.orders'))
    
    if request.method == 'POST':
        status = request.form.get('status')
        cost = request.form.get('cost')
        notes = request.form.get('notes')
        
        old_status = order['status']
        
        try:
            db.execute('''
                UPDATE orders SET status = ?, cost = ?, notes = ? WHERE id = ?
            ''', (status, cost, notes, order_id))
            
            if old_status != status:
                db.execute('''
                    INSERT INTO order_status_history (order_id, old_status, new_status, changed_by_id, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, old_status, status, session['user_id'], 'Статус изменен'))
                
                # Если заказ доставлен, освобождаем транспорт и водителя
                if status == 'Доставлен':
                    route = db.execute('SELECT driver_id, vehicle_id FROM routes WHERE order_id = ?', (order_id,)).fetchone()
                    if route:
                        db.execute('UPDATE vehicles SET status = ? WHERE id = ?', ('Свободен', route['vehicle_id']))
                        db.execute('UPDATE drivers SET is_available = ? WHERE id = ?', (1, route['driver_id']))
                        db.execute('UPDATE routes SET status = ? WHERE order_id = ?', ('Завершен', order_id))
            
            db.commit()
            flash('Заказ обновлен', 'success')
            return redirect(url_for('logistic.orders'))
        
        except Exception as e:
            db.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    db.close()
    
    return render_template('logistic/edit_order.html', order=order)

@logistic_bp.route('/vehicles')
@role_required('Логист', 'Администратор')
def vehicles():
    """Список транспортных средств"""
    db = get_db()
    
    status_filter = request.args.get('status', '')
    
    query = 'SELECT * FROM vehicles WHERE 1=1'
    params = []
    
    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY brand, model'
    
    vehicles_list = db.execute(query, params).fetchall()
    statuses = db.execute('SELECT DISTINCT status FROM vehicles').fetchall()
    
    db.close()
    
    return render_template('logistic/vehicles.html', vehicles=vehicles_list, statuses=statuses, current_status=status_filter)

@logistic_bp.route('/routes')
@role_required('Логист', 'Администратор')
def routes():
    """Список маршрутов"""
    db = get_db()
    
    status_filter = request.args.get('status', '')
    
    query = '''
        SELECT r.id, r.order_id, o.order_number, d.full_name, v.brand, v.model, 
               v.license_plate, r.status, r.planned_start_time, r.planned_end_time
        FROM routes r
        JOIN orders o ON r.order_id = o.id
        LEFT JOIN drivers d ON r.driver_id = d.id
        LEFT JOIN vehicles v ON r.vehicle_id = v.id
        WHERE 1=1
    '''
    params = []
    
    if status_filter:
        query += ' AND r.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY r.planned_start_time DESC'
    
    routes_list = db.execute(query, params).fetchall()
    statuses = db.execute('SELECT DISTINCT status FROM routes').fetchall()
    
    db.close()
    
    return render_template('logistic/routes.html', routes=routes_list, statuses=statuses, current_status=status_filter)

@logistic_bp.route('/warehouse')
@role_required('Логист', 'Администратор')
def warehouse():
    """Управление складом"""
    db = get_db()
    
    status_filter = request.args.get('status', '')
    zone_filter = request.args.get('zone', '')
    
    query = 'SELECT * FROM warehouse WHERE 1=1'
    params = []
    
    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    
    if zone_filter:
        query += ' AND storage_zone = ?'
        params.append(zone_filter)
    
    query += ' ORDER BY storage_zone, cargo_name'
    
    items = db.execute(query, params).fetchall()
    
    # Статистика
    stats = {
        'total_items': db.execute('SELECT COUNT(*) as count FROM warehouse').fetchone()['count'],
        'total_volume': db.execute('SELECT SUM(volume) as sum FROM warehouse').fetchone()['sum'] or 0,
    }
    
    statuses = db.execute('SELECT DISTINCT status FROM warehouse').fetchall()
    zones = db.execute('SELECT DISTINCT storage_zone FROM warehouse').fetchall()
    
    db.close()
    
    return render_template('logistic/warehouse.html', items=items, stats=stats, statuses=statuses, zones=zones, current_status=status_filter, current_zone=zone_filter)

# ============ ВОДИТЕЛЬ ============
@driver_bp.route('/dashboard')
@role_required('Водитель')
def dashboard():
    """Панель водителя"""
    db = get_db()
    
    user_id = session['user_id']
    
    # Получить ID водителя
    driver = db.execute('SELECT id FROM drivers WHERE user_id = ?', (user_id,)).fetchone()
    
    if not driver:
        flash('Профиль водителя не найден', 'danger')
        return redirect(url_for('auth.logout'))
    
    driver_id = driver['id']
    
    stats = {
        'active_routes': db.execute('SELECT COUNT(*) as count FROM routes WHERE driver_id = ? AND status IN ("В пути", "Запланирован")', (driver_id,)).fetchone()['count'],
        'completed_routes': db.execute('SELECT COUNT(*) as count FROM routes WHERE driver_id = ? AND status = "Завершен"', (driver_id,)).fetchone()['count'],
        'unread_notifications': db.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,)).fetchone()['count'],
    }
    
    my_routes = db.execute('''
        SELECT r.id, o.order_number, o.address_from, o.address_to, r.status, r.planned_start_time
        FROM routes r
        JOIN orders o ON r.order_id = o.id
        WHERE r.driver_id = ?
        ORDER BY r.planned_start_time DESC LIMIT 10
    ''', (driver_id,)).fetchall()
    
    db.close()
    
    return render_template('driver/dashboard.html', stats=stats, my_routes=my_routes)

@driver_bp.route('/routes')
@role_required('Водитель')
def routes():
    """Мои маршруты"""
    db = get_db()
    
    user_id = session['user_id']
    driver = db.execute('SELECT id FROM drivers WHERE user_id = ?', (user_id,)).fetchone()
    
    if not driver:
        flash('Профиль водителя не найден', 'danger')
        return redirect(url_for('auth.logout'))
    
    driver_id = driver['id']
    
    my_routes = db.execute('''
        SELECT r.id, r.order_id, o.order_number, o.address_from, o.address_to, o.cargo_description,
               o.weight, r.status, r.planned_start_time, r.planned_end_time, v.brand, v.model
        FROM routes r
        JOIN orders o ON r.order_id = o.id
        LEFT JOIN vehicles v ON r.vehicle_id = v.id
        WHERE r.driver_id = ?
        ORDER BY r.planned_start_time DESC
    ''', (driver_id,)).fetchall()
    
    db.close()
    
    return render_template('driver/routes.html', routes=my_routes)

@driver_bp.route('/routes/<int:route_id>/update-status', methods=['POST'])
@role_required('Водитель')
def update_route_status(route_id):
    """Обновление статуса маршрута"""
    db = get_db()
    
    user_id = session['user_id']
    driver = db.execute('SELECT id FROM drivers WHERE user_id = ?', (user_id,)).fetchone()
    
    if not driver:
        return jsonify({'success': False, 'message': 'Профиль водителя не найден'})
    
    route = db.execute('SELECT * FROM routes WHERE id = ? AND driver_id = ?', (route_id, driver['id'])).fetchone()
    
    if not route:
        return jsonify({'success': False, 'message': 'Маршрут не найден'})
    
    new_status = request.json.get('status')
    
    try:
        if new_status == 'В пути':
            db.execute('UPDATE routes SET status = ?, actual_start_time = ? WHERE id = ?',
                      (new_status, datetime.now(), route_id))
        elif new_status == 'Завершен':
            db.execute('UPDATE routes SET status = ?, actual_end_time = ? WHERE id = ?',
                      (new_status, datetime.now(), route_id))
            
            # Обновить статус заказа
            order_id = route['order_id']
            db.execute('UPDATE orders SET status = ?, actual_delivery_date = ? WHERE id = ?',
                      ('Доставлен', datetime.now().date(), order_id))
            
            # Освободить транспорт и водителя
            db.execute('UPDATE vehicles SET status = ? WHERE id = ?', ('Свободен', route['vehicle_id']))
            db.execute('UPDATE drivers SET is_available = ? WHERE id = ?', (1, driver['id']))
        
        db.commit()
        return jsonify({'success': True, 'message': 'Статус обновлен'})
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        db.close()

@driver_bp.route('/notifications')
@role_required('Водитель')
def notifications():
    """Уведомления водителя"""
    db = get_db()
    
    user_id = session['user_id']
    
    notifs = db.execute('''
        SELECT id, message, type, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    db.close()
    
    return render_template('driver/notifications.html', notifications=notifs)

# ============ API ============
@api_bp.route('/available-vehicles')
@login_required
def get_available_vehicles():
    """API: получить доступный транспорт"""
    required_capacity = request.args.get('capacity', type=float, default=0)
    
    db = get_db()
    vehicles = db.execute('''
        SELECT id, brand, model, license_plate, capacity
        FROM vehicles
        WHERE status = 'Свободен' AND capacity >= ?
        ORDER BY capacity
    ''', (required_capacity,)).fetchall()
    db.close()
    
    return jsonify([dict(v) for v in vehicles])

@api_bp.route('/available-drivers')
@login_required
def get_available_drivers():
    """API: получить доступных водителей"""
    db = get_db()
    drivers = db.execute('''
        SELECT id, full_name, experience_years, license_number
        FROM drivers
        WHERE is_available = 1
    ''').fetchall()
    db.close()
    
    return jsonify([dict(d) for d in drivers])

@api_bp.route('/order-status-history/<int:order_id>')
@login_required
def get_order_status_history(order_id):
    """API: история статусов заказа"""
    db = get_db()
    history = db.execute('''
        SELECT old_status, new_status, changed_at, notes
        FROM order_status_history
        WHERE order_id = ?
        ORDER BY changed_at DESC
    ''', (order_id,)).fetchall()
    db.close()
    
    return jsonify([dict(h) for h in history])
