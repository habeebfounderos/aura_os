from flask import Blueprint, request, jsonify
from src.models.user import User, db

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/register", methods=["POST"])
def register_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 409

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@user_bp.route("/user/login", methods=["POST"])
def login_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

@user_bp.route("/user/profile", methods=["GET"])
def get_user_profile():
    # This is a placeholder. In a real app, you would use tokens for authentication.
    return jsonify({"username": "test_user", "email": "test@example.com"}), 200
