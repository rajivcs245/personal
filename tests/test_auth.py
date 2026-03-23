import pytest
from app import app
from utils import get_db_connection
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data

def test_signup_process(client):
    # Use a unique email
    email = "new_user_pytest@example.com"
    
    # Cleanup if exists
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email=%s", (email,))
    conn.commit()
    conn.close()

    response = client.post('/signup', data={
        'name': 'Pytest Signup',
        'email': email,
        'password': 'password123',
        'role': 'user'
    }, follow_redirects=True)
    
    assert b"Signup successful" in response.data
    
    # Verify in DB
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    assert cur.fetchone() is not None
    conn.close()

def test_unauthorized_dashboard_access(client):
    # Try accessing admin dashboard without login
    response = client.get('/admin_dashboard', follow_redirects=True)
    assert b"Please login first" in response.data
