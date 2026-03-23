from werkzeug.security import generate_password_hash
import sys
from utils import get_db_connection
from app import app

def migrate_passwords():
    """Migrates plain text passwords to Werkzeug hashes."""
    print("\n--- PASSWORD MIGRATION ---")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, password FROM users")
        users = cur.fetchall()
        
        count = 0
        for user in users:
            pwd = user['password']
            if not (pwd.startswith('scrypt:') or pwd.startswith('pbkdf2:')):
                print(f"Hashing password for: {user['email']}")
                hashed_pwd = generate_password_hash(pwd)
                cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed_pwd, user['id']))
                count += 1
                
        conn.commit()
        conn.close()
        print(f"Successfully migrated {count} passwords.")
    except Exception as e:
        print(f"Migration Error: {e}")

def list_routes():
    """Lists all registered routes in the application."""
    print("\n--- APPLICATION ROUTES ---")
    with app.app_context():
        for rule in app.url_map.iter_rules():
            print(f"Endpoint: {rule.endpoint:30} Methods: {str(list(rule.methods)):30} Path: {rule}")

def list_users():
    """Lists users registered in the database."""
    print("\n--- REGISTERED USERS ---")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, role, is_active FROM users")
        for row in cur.fetchall():
            active_status = "Active" if row.get('is_active', 1) else "Deactivated"
            print(f"ID: {row['id']:<4} | Name: {row['name']:<15} | Email: {row['email']:<25} | Role: {row['role']:<10} | Status: {active_status}")
        conn.close()
    except Exception as e:
        print(f"Error fetching users: {e}")

def debug_db():
    """Detailed debug output of bookings, services, and earnings."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("\n--- RECENT BOOKINGS ---")
        cur.execute("SELECT b.id, s.service_name, u.name as user, b.booking_date, b.status FROM bookings b JOIN services s ON b.service_id = s.id JOIN users u ON b.user_id = u.id LIMIT 10")
        for row in cur.fetchall():
            print(row)
            
        print("\n--- APPROVED SERVICES ---")
        cur.execute("SELECT id, service_name, location, cost, status FROM services WHERE status='Approved'")
        for row in cur.fetchall():
            print(row)
            
        print("\n--- PROVIDER EARNINGS ---")
        cur.execute("""
            SELECT p.id, p.name, COALESCE(SUM(b.amount), 0) AS total_earnings
            FROM users p
            LEFT JOIN services s ON s.provider_id = p.id
            LEFT JOIN bookings b ON b.service_id = s.id AND b.status='Completed'
            WHERE p.role='provider'
            GROUP BY p.id, p.name
            ORDER BY total_earnings DESC
        """)
        for row in cur.fetchall():
            print(f"Provider ID: {row['id']:<4} | Name: {row['name']:<15} | Total Earnings: ₹{row['total_earnings']}")
            
        conn.close()
    except Exception as e:
        print(f"Debug Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py [routes|users|debug]")
        return

    command = sys.argv[1].lower()
    if command == "routes":
        list_routes()
    elif command == "users":
        list_users()
    elif command == "debug":
        debug_db()
    elif command == "migrate":
        migrate_passwords()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: routes, users, debug, migrate")

if __name__ == "__main__":
    main()
