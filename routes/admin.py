from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils import get_db_connection, login_required, role_required
from utils.profile import handle_profile_update, handle_photo_removal
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    admin_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, email, profile_photo, description FROM users WHERE id = %s", (admin_id,))
    admin = cur.fetchone()
    
    # Extract values from admin dict (handling potential None results gracefully)
    if admin:
        admin_name = admin.get('name', 'Admin')
        profile_photo = admin.get('profile_photo') or 'default.png'
        admin_description = admin.get('description') or 'Administrator'
    else:
        admin_name = "Admin"
        profile_photo = "default.png"
        admin_description = "Administrator"

    # Fetch Counts for Dashboard
    cur.execute("SELECT COUNT(*) as count FROM users WHERE role='provider'")
    provider_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM users WHERE role='user'")
    user_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM services WHERE status='Approved'")
    service_count = cur.fetchone()['count']
    
    cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM bookings WHERE status='Completed'")
    total_revenue = cur.fetchone()['total']
    
    # Fetch Recent Bookings
    cur.execute("""
        SELECT b.id, u.name as user_name, s.service_name, b.amount, b.status, b.booking_date 
        FROM bookings b 
        JOIN users u ON b.user_id = u.id 
        JOIN services s ON b.service_id = s.id 
        ORDER BY b.id DESC LIMIT 5
    """)
    recent_bookings = cur.fetchall()

    conn.close()
    
    return render_template('admin_dashboard.html', 
                           admin_name=admin_name, 
                           profile_photo=profile_photo, 
                           admin_description=admin_description,
                           provider_count=provider_count,
                           user_count=user_count,
                           service_count=service_count,
                           total_revenue=total_revenue,
                           recent_bookings=recent_bookings)

@admin_bp.route('/admin_profile')
@login_required
@role_required('admin')
def admin_profile():
    admin_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, email, profile_photo, description FROM users WHERE id = %s", (admin_id,))
    admin = cur.fetchone()
    conn.close()
    
    if not admin:
        flash("Admin details not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin_profile.html', 
                           admin_name=admin['name'], 
                           email=admin['email'],
                           profile_photo=admin.get("profile_photo") or "default.png", 
                           admin_description=admin.get("description") or "Administrator account")

@admin_bp.route('/admin/pending_services')
@login_required
@role_required('admin')
def admin_pending_services():
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetching both Pending and Processed (Approved/Rejected) services
    cur.execute("""
        SELECT s.id, s.service_name, s.location, s.cost, s.status, u.name as provider_name 
        FROM services s 
        JOIN users u ON s.provider_id = u.id
        WHERE s.status IN ('Pending', 'Approved', 'Rejected')
        ORDER BY FIELD(s.status, 'Pending', 'Approved', 'Rejected'), s.id DESC
    """)
    services = cur.fetchall()
    conn.close()
    return render_template('admin_pending_services.html', services=services)

@admin_bp.route('/admin_approve_service/<int:service_id>')
@login_required
@role_required('admin')
def admin_approve_service(service_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch service to get provider_id
    cur.execute("SELECT provider_id FROM services WHERE id=%s", (service_id,))
    row = cur.fetchone()
    
    if not row:
        conn.close()
        flash("Service not found.", "danger")
        return redirect(url_for('admin.admin_pending_services'))
        
    provider_id = row['provider_id']
    cur.execute("UPDATE services SET status='Approved' WHERE id=%s", (service_id,))
    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", (provider_id, "Your service has been APPROVED by admin"))
    conn.commit()
    conn.close()
    flash("Service approved successfully!", "success")
    return redirect(url_for('admin.admin_pending_services'))

@admin_bp.route('/admin_reject_service/<int:service_id>')
@login_required
@role_required('admin')
def admin_reject_service(service_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch service to get provider_id
    cur.execute("SELECT provider_id FROM services WHERE id=%s", (service_id,))
    row = cur.fetchone()
    
    if not row:
        conn.close()
        flash("Service not found.", "danger")
        return redirect(url_for('admin.admin_pending_services'))
        
    provider_id = row['provider_id']
    cur.execute("UPDATE services SET status='Rejected' WHERE id=%s", (service_id,))
    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", (provider_id, "Your service has been REJECTED by admin"))
    conn.commit()
    conn.close()
    flash("Service rejected successfully!", "danger")
    return redirect(url_for('admin.admin_pending_services'))
@admin_bp.route('/admin_report')
@login_required
@role_required('admin')
def admin_report():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # ================= WEEKLY =================
    cur.execute("""
        SELECT COUNT(*) AS total_bookings, COALESCE(SUM(amount),0) AS total_revenue
        FROM bookings WHERE status='Completed' AND YEARWEEK(booking_date, 1) = YEARWEEK(CURDATE(), 1)
    """)
    weekly = cur.fetchone() or {'total_bookings': 0, 'total_revenue': 0}
    
    # ================= MONTHLY =================
    cur.execute("""
        SELECT COUNT(*) AS total_bookings, COALESCE(SUM(amount),0) AS total_revenue
        FROM bookings WHERE status='Completed' AND YEAR(booking_date) = YEAR(CURDATE()) AND MONTH(booking_date) = MONTH(CURDATE())
    """)
    monthly = cur.fetchone() or {'total_bookings': 0, 'total_revenue': 0}
    
    # ================= YEARLY =================
    cur.execute("""
        SELECT COUNT(*) AS total_bookings, COALESCE(SUM(amount),0) AS total_revenue
        FROM bookings WHERE status='Completed' AND YEAR(booking_date) = YEAR(CURDATE())
    """)
    yearly = cur.fetchone() or {'total_bookings': 0, 'total_revenue': 0}
    
    # ================= ALL PROVIDERS EARNINGS =================
    cur.execute("""
        SELECT p.name, COALESCE(SUM(b.amount),0) AS total_earnings
        FROM users p
        LEFT JOIN services s ON s.provider_id = p.id
        LEFT JOIN bookings b ON b.service_id = s.id AND b.status='Completed'
        WHERE p.role='provider'
        GROUP BY p.id, p.name
        ORDER BY total_earnings DESC
    """)
    provider_earnings = cur.fetchall()
    conn.close()

    return render_template('admin_report.html', weekly_bookings=weekly['total_bookings'], weekly_revenue=float(weekly['total_revenue']),
                           monthly_bookings=monthly['total_bookings'], monthly_revenue=float(monthly['total_revenue']),
                           yearly_bookings=yearly['total_bookings'], yearly_revenue=float(yearly['total_revenue']), provider_earnings=provider_earnings)

@admin_bp.route("/update_admin_profile", methods=["POST"])
@login_required
@role_required('admin')
def update_admin_profile():
    handle_profile_update(request, 'admin')
    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route("/remove_admin_photo", methods=["POST"])
@login_required
@role_required('admin')
def remove_admin_photo():
    handle_photo_removal()
    return redirect(url_for("admin.admin_dashboard"))
@admin_bp.route('/admin/manage_providers')
@login_required
@role_required('admin')
def manage_providers():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, is_active, verification_status, business_name, phone, address FROM users WHERE role = 'provider'")
    providers = cur.fetchall()
    conn.close()
    return render_template('admin_manage_providers.html', providers=providers)

@admin_bp.route('/admin/toggle_provider_status/<int:provider_id>')
@login_required
@role_required('admin')
def toggle_provider_status(provider_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Check if user is a provider
    cur.execute("SELECT role, is_active FROM users WHERE id = %s", (provider_id,))
    user = cur.fetchone()
    if user and user['role'] == 'provider':
        new_status = 0 if user['is_active'] else 1
        cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_status, provider_id))
        
        # Notify provider of status change
        status_text = "Deactivated" if new_status == 0 else "Activated"
        msg = f"Your service provider account has been {status_text} by the administrator."
        cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", (provider_id, msg))
        
        conn.commit()
        status_text = "Deactivated" if new_status == 0 else "Activated"
        flash(f"Provider account {status_text} successfully.", "success")
    else:
        flash("Invalid provider ID.", "danger")
    conn.close()
    return redirect(url_for('admin.manage_providers'))
@admin_bp.route('/admin/pending_verifications')
@login_required
@role_required('admin')
def admin_pending_verifications():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Combined query for Pending and Verified
    cur.execute("""
        SELECT id, name, email, business_name, phone, address, id_proof_number, id_proof_image, verification_submitted_at, verification_status
        FROM users 
        WHERE role = 'provider' AND verification_status IN ('Pending', 'Verified')
        ORDER BY FIELD(verification_status, 'Pending', 'Verified'), verification_submitted_at DESC
    """)
    all_providers = cur.fetchall()
    
    # Calculate counts for the UI banner
    pending_count = sum(1 for p in all_providers if p['verification_status'] == 'Pending')
    
    conn.close()
    return render_template('admin_pending_verifications.html', providers=all_providers, pending_count=pending_count)

@admin_bp.route('/admin_approve_provider/<int:provider_id>')
@login_required
@role_required('admin')
def admin_approve_provider(provider_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET verification_status='Verified' WHERE id=%s", (provider_id,))
    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", 
                (provider_id, "Congratulations! Your provider account has been VERIFIED. You can now post services."))
    conn.commit()
    conn.close()
    flash("Provider verified successfully!", "success")
    return redirect(url_for('admin.admin_pending_verifications'))

@admin_bp.route('/admin_reject_provider/<int:provider_id>')
@login_required
@role_required('admin')
def admin_reject_provider(provider_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET verification_status='Rejected' WHERE id=%s", (provider_id,))
    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", 
                (provider_id, "Your verification request was REJECTED. Please update your details and submit again."))
    conn.commit()
    conn.close()
    flash("Provider verification rejected.", "danger")
    return redirect(url_for('admin.admin_pending_verifications'))
