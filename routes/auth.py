from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from utils import get_db_connection
import secrets
from datetime import datetime, timedelta
import pytz

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
            flash("❌ Password must be at least 8 characters and contain both letters and numbers.", "danger")
            return redirect(url_for('auth.signup'))

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            conn.close()
            flash("Email already registered", "danger")
            return redirect(url_for('auth.signup'))

        # Hash password before storing
        hashed_pw = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (%s, %s, %s, %s)
        """, (name, email, hashed_pw, role))

        conn.commit()
        conn.close()

        flash("Signup successful. Please login.", "success")
        return redirect(url_for('auth.login'))

    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        selected_role = request.form['role']

        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch user by email first
        cur.execute("SELECT id, name, password, role, is_active FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        conn.close()

        if user:
            # 1. Check if the role matches
            if user['role'] != selected_role:
                flash(f"⚠ Please check the role! You are registered as {user['role'].upper()}.", "warning")
            # 2. Check the password
            elif check_password_hash(user['password'], password):
                # 3. Check if account is active
                if 'is_active' in user and user['is_active'] == 0:
                    flash("❌ Your account has been deactivated by the administrator. Please contact support.", "danger")
                    return redirect(url_for('auth.login'))

                session['user_id'] = user['id']
                session['role'] = user['role']
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin.admin_dashboard'))
                elif user['role'] == 'provider':
                    return redirect(url_for('provider.provider_dashboard'))
                else:
                    return redirect(url_for('user.user_dashboard'))
            else:
                flash("Invalid password. Please try again.", "danger")
        else:
            flash("Invalid email or password. Please try again.", "danger")
        return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        
        if user:
            # Generate a secure token
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            
            cur.execute("""
                UPDATE users 
                SET reset_token=%s, token_expiry=%s 
                WHERE id=%s
            """, (token, expiry, user['id']))
            conn.commit()
            conn.close()
            
            # Since we can't send real emails, we flash the link for dev/testing
            flash(f"✅ Reset link generated (Simulated Email): Reset Token is {token}", "success")
            return redirect(url_for('auth.reset_password', email=email))
        else:
            conn.close()
            flash("❌ That email address is not registered.", "danger")
            return render_template('forgot_password_form.html')
        
    return render_template('forgot_password_form.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email') or request.form.get('email')
    if request.method == 'POST':
        token = request.form.get('token')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash("❌ Passwords do not match!", "danger")
            return render_template('reset_password.html', email=email)
            
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, token_expiry FROM users WHERE email=%s AND reset_token=%s", (email, token))
        user = cur.fetchone()
        
        if user:
            if user['token_expiry'] > datetime.now():
                hashed_pw = generate_password_hash(new_password)
                cur.execute("UPDATE users SET password=%s, reset_token=NULL, token_expiry=NULL WHERE id=%s", (hashed_pw, user['id']))
                conn.commit()
                conn.close()
                flash("✅ Password updated successfully!", "success")
                return redirect(url_for('auth.login'))
            else:
                flash("❌ Token has expired.", "danger")
        else:
            flash("❌ Invalid token or email.", "danger")
            
        conn.close()
        return render_template('reset_password.html', email=email)
        
    return render_template('reset_password.html', email=email)

