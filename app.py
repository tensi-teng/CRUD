from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from sqlalchemy.exc import IntegrityError
import os
from datetime import timedelta

app = Flask(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dev.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    reg_number = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    fitness_items = db.relationship('FitnessItem', backref='user', cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'reg_number': self.reg_number
        }

class FitnessItem(db.Model):
    __tablename__ = 'fitness_items'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id
        }


with app.app_context():
    db.create_all()

# Routes
@app.route('/register', methods=['POST'])
def register():
    """Register new user. Expects JSON with name, reg_number, password."""
    data = request.get_json() or {}
    name = data.get('name')
    reg_number = data.get('reg_number')
    password = data.get('password')

    if not name or not reg_number or not password:
        return jsonify({'msg': 'name, reg_number and password are required'}), 400

    if User.query.filter_by(reg_number=reg_number).first():
        return jsonify({'msg': 'reg_number already exists'}), 409

    user = User(name=name, reg_number=reg_number)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'msg': 'reg_number already exists'}), 409

    return jsonify({'msg': 'user created', 'user': user.to_dict()}), 201

@app.route('/login', methods=['POST'])
def login():
    """Login user. Expects JSON with reg_number and password."""
    data = request.get_json() or {}
    reg_number = data.get('reg_number')
    password = data.get('password')

    if not reg_number or not password:
        return jsonify({'msg': 'reg_number and password are required'}), 400

    user = User.query.filter_by(reg_number=reg_number).first()
    if not user or not user.check_password(password):
        return jsonify({'msg': 'invalid credentials'}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': access_token, 'user': user.to_dict()}), 200


def get_current_user():
    identity = get_jwt_identity()
    if identity is None:
        return None
   
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return User.query.get(user_id)

# Fitness CRUD
@app.route('/fitness', methods=['POST'])
@jwt_required()
def create_fitness_item():
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description')

    if not title:
        return jsonify({'msg': 'title is required'}), 400

    user = get_current_user()
    if user is None:
        return jsonify({'msg': 'invalid or expired token'}), 401

    item = FitnessItem(title=title, description=description, user_id=user.id)
    db.session.add(item)
    db.session.commit()

    return jsonify({'msg': 'created', 'item': item.to_dict()}), 201

@app.route('/fitness', methods=['GET'])
@jwt_required()
def list_fitness_items():
    user = get_current_user()
    if user is None:
        return jsonify({'msg': 'invalid or expired token'}), 401

    items = FitnessItem.query.filter_by(user_id=user.id).all()
    return jsonify({'items': [i.to_dict() for i in items]}), 200

@app.route('/fitness/<int:item_id>', methods=['GET'])
@jwt_required()
def get_fitness_item(item_id):
    user = get_current_user()
    if user is None:
        return jsonify({'msg': 'invalid or expired token'}), 401

    item = FitnessItem.query.filter_by(id=item_id, user_id=user.id).first()
    if not item:
        return jsonify({'msg': 'not found'}), 404
    return jsonify({'item': item.to_dict()}), 200

@app.route('/fitness/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_fitness_item(item_id):
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description')

    user = get_current_user()
    if user is None:
        return jsonify({'msg': 'invalid or expired token'}), 401

    item = FitnessItem.query.filter_by(id=item_id, user_id=user.id).first()
    if not item:
        return jsonify({'msg': 'not found'}), 404

    if title:
        item.title = title
    if description is not None:
        item.description = description

    db.session.commit()
    return jsonify({'msg': 'updated', 'item': item.to_dict()}), 200

@app.route('/fitness/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_fitness_item(item_id):
    user = get_current_user()
    if user is None:
        return jsonify({'msg': 'invalid or expired token'}), 401

    item = FitnessItem.query.filter_by(id=item_id, user_id=user.id).first()
    if not item:
        return jsonify({'msg': 'not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'msg': 'deleted'}), 200


@app.route('/ping')
def ping():
    return jsonify({'msg': 'pong'}), 200

if __name__ == '__main__':
    
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=debug_mode)
