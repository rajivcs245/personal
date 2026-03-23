import pymysql
from config import Config
from functools import wraps
from flask import session, redirect, url_for, flash

def get_db_connection():
    """Returns a new database connection."""
    return pymysql.connect(
        host=Config.DATABASE_HOST,
        user=Config.DATABASE_USER,
        password=Config.DATABASE_PASSWORD,
        database=Config.DATABASE_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def login_required(f):
    """Decorator to ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first!", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    """Decorator to ensure user has a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session.get('role') != role:
                flash("Access denied! Insufficient permissions.", "danger")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
