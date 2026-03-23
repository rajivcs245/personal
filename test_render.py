from app import app
from flask import url_for, render_template
from utils import get_db_connection
import os

with app.test_request_context():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, is_active, verification_status FROM users WHERE role = 'provider'")
    providers = cur.fetchall()
    conn.close()
    
    html = render_template('admin_manage_providers.html', providers=providers)
    print(html)
