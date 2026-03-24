from app import app
from flask import render_template
from utils import get_db_connection
from werkzeug.security import generate_password_hash
import pytest

def get_render_data(role='provider', status='Pending'):
    with app.app_context():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, business_name, phone, address, id_proof_number, id_proof_image, verification_submitted_at FROM users WHERE role = %s AND verification_status = %s", (role, status))
        results = cur.fetchall()
        conn.close()
        return results

def test_admin_manage_providers_render():
    """Smoke test for admin provider management template rendering."""
    with app.test_request_context():
        providers = get_render_data('provider', 'Verified')
        html = render_template('admin_manage_providers.html', providers=providers)
        assert "Manage Service Providers" in html

def test_admin_pending_verifications_render():
    """Smoke test for admin pending verifications template rendering."""
    with app.test_request_context():
        pending = get_render_data('provider', 'Pending')
        verified = get_render_data('provider', 'Verified')
        html = render_template('admin_pending_verifications.html', verifications=pending, verified_providers=verified)
        assert "Provider Verifications" in html

def test_login_and_dashboard_flow():
    """Test integration flow for user login and dashboard access."""
    app.config['TESTING'] = True
    client = app.test_client()
    
    email = "test_integration_user@example.com"
    pw = "password123"
    
    with app.app_context():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email=%s", (email,))
        hashed_pw = generate_password_hash(pw)
        cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                    ("Integration User", email, hashed_pw, "user"))
        conn.commit()
        conn.close()
    
    # Login Attempt
    res = client.post('/login', data={'email': email, 'password': pw, 'role': 'user'}, follow_redirects=True)
    body = res.data.decode()
    assert "Available Services" in body
    assert "Your account has been deactivated" not in body
