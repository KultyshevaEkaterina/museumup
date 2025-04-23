
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt
from passlib.hash import pbkdf2_sha256
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///museum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "super-secret")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)

    def check_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)

# Модели музея
class Exhibit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    status = db.Column(db.String(50), default="on display")

class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    floor = db.Column(db.Integer)

class Exhibition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date_start = db.Column(db.Date)
    date_end = db.Column(db.Date)

class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exhibit_id = db.Column(db.Integer, db.ForeignKey('exhibit.id'))
    action = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Декоратор для администраторского доступа
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not claims.get("is_admin", False):
            return jsonify({"msg": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

# Аутентификация
@app.route('/api/v1/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.username, additional_claims={"is_admin": user.is_admin})
        return jsonify(access_token=access_token), 200
    return jsonify(msg="Bad username or password"), 401

# Работа с экспонатами
@app.route('/api/v1/exhibits', methods=['GET'])
@jwt_required()
def get_exhibits():
    exhibits = Exhibit.query.all()
    return jsonify([{"id": e.id, "name": e.name, "status": e.status} for e in exhibits])

@app.route('/api/v1/exhibits', methods=['POST'])
@jwt_required()
@admin_required
def add_exhibit():
    data = request.get_json()
    new_exhibit = Exhibit(
        name=data['name'],
        description=data.get('description'),
        location=data.get('location'),
        status=data.get('status', 'on display')
    )
    db.session.add(new_exhibit)
    db.session.commit()
    return jsonify(msg="Exhibit added"), 201

@app.route('/api/v1/exhibits/<int:exhibit_id>', methods=['GET'])
@jwt_required()
def get_exhibit(exhibit_id):
    exhibit = Exhibit.query.get_or_404(exhibit_id)
    return jsonify({
        "id": exhibit.id,
        "name": exhibit.name,
        "description": exhibit.description,
        "location": exhibit.location,
        "status": exhibit.status
    })
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
@app.route('/api/v1/halls/<int:id>', methods=['PUT'])
@jwt_required()
def update_hall(id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user or not user.is_admin:
        return jsonify({'message': 'Access denied'}), 403

    hall = Hall.query.get(id)
    if not hall:
        return jsonify({'message': 'Hall not found'}), 404

    data = request.get_json()
    if 'name' in data:
        hall.name = data['name']
    if 'floor' in data:
        hall.floor = data['floor']

    db.session.commit()
    return jsonify({
        'message': 'Hall updated successfully',
        'hall': {
            'id': hall.id,
            'name': hall.name,
            'floor': hall.floor
        }
    }), 200
@app.route('/')
def index():
    return "Hello from Flask inside Docker!"

@app.route('/api/v1/exhibits/<int:exhibit_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_exhibit(exhibit_id):
    exhibit = Exhibit.query.get_or_404(exhibit_id)
    data = request.get_json()
    exhibit.name = data.get('name', exhibit.name)
    exhibit.description = data.get('description', exhibit.description)
    exhibit.location = data.get('location', exhibit.location)
    exhibit.status = data.get('status', exhibit.status)
    db.session.commit()
    return jsonify(msg="Exhibit updated")

@app.route('/api/v1/exhibits/<int:exhibit_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_exhibit(exhibit_id):
    exhibit = Exhibit.query.get_or_404(exhibit_id)
    db.session.delete(exhibit)
    db.session.commit()
    return jsonify(msg="Exhibit deleted")

@app.route('/api/v1/exhibits/<int:exhibit_id>/move', methods=['POST'])
@jwt_required()
@admin_required
def move_exhibit(exhibit_id):
    data = request.get_json()
    exhibit = Exhibit.query.get_or_404(exhibit_id)
    old_status = exhibit.status
    exhibit.status = data.get('status', old_status)
    db.session.commit()
    journal = Journal(exhibit_id=exhibit.id, action=f"Moved from {old_status} to {exhibit.status}")
    db.session.add(journal)
    db.session.commit()
    return jsonify(msg=f"Exhibit moved to {exhibit.status}")

# Инициализация базы данных и создание администратора
@app.route('/init-db')
def init_db():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    return "Database initialized with admin user!"
@app.route('/populate-db')
def populate_db():
    # Пользователи
    for i in range(5):
        user = User(username=f'user{i}', is_admin=(i == 0))
        user.set_password(f'password{i}')
        db.session.add(user)

    # Залы
    for i in range(5):
        hall = Hall(name=f'Hall {i+1}', floor=(i % 3) + 1)
        db.session.add(hall)

    # Экспонаты
    for i in range(5):
        exhibit = Exhibit(
            name=f'Exhibit {i+1}',
            description=f'Description for exhibit {i+1}',
            location=f'Hall {(i % 5) + 1}',
            status='on display' if i % 2 == 0 else 'in storage'
        )
        db.session.add(exhibit)

    # Экспозиции
    today = datetime.utcnow().date()
    for i in range(5):
        exhibition = Exhibition(
            title=f'Exhibition {i+1}',
            description=f'About exhibition {i+1}',
            date_start=today - timedelta(days=30 * i),
            date_end=today + timedelta(days=30 * (i+1))
        )
        db.session.add(exhibition)

    # Журнал
    for i in range(5):
        journal = Journal(
            exhibit_id=(i % 5) + 1,
            action='moved to restoration' if i % 2 == 0 else 'returned to display',
            timestamp=datetime.utcnow() - timedelta(days=i)
        )
        db.session.add(journal)

    db.session.commit()
    return 'База данных успешно заполнена тестовыми данными!'

if __name__ == '__main__':
    app.run(debug=True)



