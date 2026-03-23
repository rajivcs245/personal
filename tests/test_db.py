import pytest
import pymysql
from config import Config
from werkzeug.security import generate_password_hash

@pytest.fixture
def db_conn():
    conn = pymysql.connect(
        host=Config.DATABASE_HOST,
        user=Config.DATABASE_USER,
        password=Config.DATABASE_PASSWORD,
        database=Config.DATABASE_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    yield conn
    conn.close()

def test_db_connection(db_conn):
    assert db_conn.open

def test_user_crud(db_conn):
    cur = db_conn.cursor()
    test_email = "test_pytest@example.com"
    
    # Cleanup
    cur.execute("DELETE FROM users WHERE email=%s", (test_email,))
    db_conn.commit()
    
    # Create
    hashed_pw = generate_password_hash("password123")
    cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("Pytest User", test_email, hashed_pw, "user"))
    db_conn.commit()
    
    # Read
    cur.execute("SELECT * FROM users WHERE email=%s", (test_email,))
    user = cur.fetchone()
    assert user is not None
    assert user['name'] == "Pytest User"
    
    # Update
    cur.execute("UPDATE users SET name=%s WHERE email=%s", ("Updated Pytest", test_email))
    db_conn.commit()
    cur.execute("SELECT name FROM users WHERE email=%s", (test_email,))
    assert cur.fetchone()['name'] == "Updated Pytest"
    
    # Delete
    cur.execute("DELETE FROM users WHERE email=%s", (test_email,))
    db_conn.commit()
    cur.execute("SELECT * FROM users WHERE email=%s", (test_email,))
    assert cur.fetchone() is None

def test_service_crud(db_conn):
    cur = db_conn.cursor()
    # Need a provider first
    cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("Test Provider", "test_prov@example.com", "pw", "provider"))
    provider_id = db_conn.insert_id()
    
    # Create Service
    cur.execute("INSERT INTO services (provider_id, service_name, location, cost, status) VALUES (%s, %s, %s, %s, %s)",
                (provider_id, "Test Cleaning", "New York", 50.00, "Approved"))
    service_id = db_conn.insert_id()
    
    # Read
    cur.execute("SELECT * FROM services WHERE id=%s", (service_id,))
    assert cur.fetchone()['service_name'] == "Test Cleaning"
    
    # Cleanup
    cur.execute("DELETE FROM services WHERE id=%s", (service_id,))
    cur.execute("DELETE FROM users WHERE id=%s", (provider_id,))
    db_conn.commit()
