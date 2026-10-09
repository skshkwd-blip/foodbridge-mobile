from flask import Blueprint, request, jsonify, session
from models import mysql

auth_bp = Blueprint('auth', __name__)

# ─────────────────────────────────────────────
# Simple in-memory user store (replace with DB table for production)
# ─────────────────────────────────────────────
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "donor": {"password": "donor123", "role": "donor"},
    "ngo":   {"password": "ngo123",   "role": "ngo"},
}


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Body: { "username": "admin", "password": "admin123" }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"}), 400

    user = USERS.get(username)
    if user and user['password'] == password:
        session['user'] = username
        session['role'] = user['role']
        return jsonify({
            "success": True,
            "message": "Login successful",
            "role": user['role'],
            "username": username
        }), 200

    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    POST /api/auth/logout
    """
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@auth_bp.route('/me', methods=['GET'])
def current_user():
    """
    GET /api/auth/me
    Returns logged-in user info from session.
    """
    if 'user' in session:
        return jsonify({
            "success": True,
            "username": session['user'],
            "role": session['role']
        }), 200
    return jsonify({"success": False, "message": "Not authenticated"}), 401