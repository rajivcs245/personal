from flask import Flask, redirect, url_for, session, flash, request
from datetime import datetime
from config import Config
from utils import get_db_connection
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.provider import provider_bp
from routes.user import user_bp
from utils.tasks import auto_complete_past_bookings, send_booking_reminders
import os

app = Flask(__name__)
app.config.from_object(Config)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(provider_bp)
app.register_blueprint(user_bp)

@app.context_processor
def inject_globals():
    data = {}
    if 'user_id' in session:
        user_id = session['user_id']
        role = session.get('role')
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Fetch user info and role-specific counts in fewer queries
            cur.execute("SELECT name, profile_photo FROM users WHERE id=%s", (user_id,))
            user = cur.fetchone()
            
            if not user:
                session.clear()
                return {}
                
            data['user_name'] = user['name']
            data['profile_photo'] = user.get('profile_photo') or 'default.png'
            
            # Use dynamic counts based on role
            if role == 'admin':
                cur.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM services WHERE status='Pending') as pending_services,
                        (SELECT COUNT(*) FROM users WHERE verification_status='Pending' AND role='provider') as pending_verifications
                """)
                counts = cur.fetchone()
                data['pending_service_count'] = counts['pending_services'] if counts else 0
                data['pending_verification_count'] = counts['pending_verifications'] if counts else 0
            elif role == 'provider':
                cur.execute("SELECT COUNT(*) AS count FROM notifications WHERE provider_id = %s AND is_read = 0", (user_id,))
                row = cur.fetchone()
                data['notification_count'] = row['count'] if row else 0
            elif role == 'user':
                cur.execute("SELECT COUNT(*) AS count FROM user_notifications WHERE user_id = %s AND is_read = 0", (user_id,))
                row = cur.fetchone()
                data['user_notification_count'] = row['count'] if row else 0
            
        except Exception as e:
            app.logger.error(f"Error in inject_globals: {e}")
        finally:
            if conn:
                conn.close()
    return data
@app.before_request
def background_tasks():
    """Run periodic background tasks without blocking the main request significantly."""
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return
        
    last_run = getattr(app, '_last_task_run', None)
    now = datetime.now()
    
    # Run only once every 2 minutes for background tasks
    if last_run is None or (now - last_run).total_seconds() > 120:
        try:
            auto_complete_past_bookings()
            send_booking_reminders()
            app._last_task_run = now
        except Exception as e:
            app.logger.error(f"Background tasks failed: {e}")

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def home():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif role == 'provider':
            return redirect(url_for('provider.provider_dashboard'))
        else:
            return redirect(url_for('user.user_dashboard'))
    return redirect(url_for('auth.login'))



@app.cli.command("send-reminders")
def send_reminders_command():
    """CLI command to send reminders."""
    send_booking_reminders()
    print("Reminders sent successfully.")

if __name__ == "__main__":
    app.run(debug=True)
