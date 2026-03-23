from app import app
from flask import url_for, render_template
from utils import get_db_connection
import os

with app.test_request_context():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Simulating what's in admin.py
    cur.execute("SELECT id, name, email, business_name, phone, address, id_proof_number, id_proof_image, verification_submitted_at FROM users WHERE role = 'provider' AND verification_status = 'Pending'")
    pending = cur.fetchall()
    
    cur.execute("SELECT id, name, email, business_name, phone, address, id_proof_number, id_proof_image, verification_submitted_at FROM users WHERE role = 'provider' AND verification_status = 'Verified'")
    verified = cur.fetchall()
    
    conn.close()
    
    html = render_template('admin_pending_verifications.html', verifications=pending, verified_providers=verified)
    print("--- PENDING COUNT ---", len(pending))
    print("--- VERIFIED COUNT ---", len(verified))
    print("--- HTML OUTPUT ---")
    print(html)
