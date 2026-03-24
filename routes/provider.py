from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils import get_db_connection, login_required, role_required
from utils.profile import handle_profile_update, handle_photo_removal
import os
from werkzeug.utils import secure_filename

provider_bp = Blueprint('provider', __name__)

@provider_bp.route('/provider_dashboard')
@login_required
@role_required('provider')
def provider_dashboard():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT name, email, profile_photo, description, verification_status, id_proof_image FROM users WHERE id = %s", (provider_id,))
    provider = cur.fetchone()

    cur.execute("SELECT id, message, is_read, created_at FROM notifications WHERE provider_id = %s ORDER BY created_at DESC", (provider_id,))
    notifications = cur.fetchall()
    
    cur.execute("""
        SELECT b.id, u.name AS user_name, s.service_name, b.booking_date, b.time_slot, b.amount, b.status
        FROM bookings b JOIN users u ON b.user_id = u.id JOIN services s ON b.service_id = s.id
        WHERE s.provider_id = %s ORDER BY b.booking_date DESC
    """, (provider_id,))
    bookings = cur.fetchall()
    
    # Optimized Counts Fetching
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM services WHERE provider_id = %s) AS total_services,
            (SELECT COUNT(*) FROM bookings b JOIN services s ON b.service_id = s.id WHERE s.provider_id = %s) AS total_bookings,
            (SELECT COUNT(*) FROM services WHERE provider_id = %s AND status = 'Pending') AS pending_requests,
            (SELECT COUNT(*) FROM notifications WHERE provider_id = %s AND is_read = 0) AS notification_count
    """, (provider_id, provider_id, provider_id, provider_id))
    
    counts = cur.fetchone()
    total_services = counts['total_services']
    total_bookings = counts['total_bookings']
    pending_requests = counts['pending_requests']
    notification_count = counts['notification_count']
    
    conn.close()
    
    provider_name = provider.get("name") if provider else "Provider"
    profile_photo = (provider.get("profile_photo") if provider else None) or "default.png"
    provider_description = (provider.get("description") if provider else None)
    description_text = provider_description or "No description added."
    verification_status = (provider.get("verification_status") if provider else "Unverified") or "Unverified"

    # Verification Progress Logic
    is_profile_complete = bool(provider_name and provider_description and profile_photo != 'default.png')
    is_services_added = total_services > 0
    is_docs_uploaded = bool(provider.get('id_proof_image'))
    is_verified = (verification_status == 'Verified')

    return render_template("provider_dashboard.html", 
                           provider_name=provider_name, 
                           profile_photo=profile_photo, 
                           provider_description=description_text, 
                           bookings=bookings, 
                           notifications=notifications, 
                           notification_count=notification_count,
                           total_services=total_services, 
                           total_bookings=total_bookings, 
                           pending_requests=pending_requests,
                           verification_status=verification_status,
                           is_profile_complete=is_profile_complete,
                           is_services_added=is_services_added,
                           is_docs_uploaded=is_docs_uploaded,
                           is_verified=is_verified)

@provider_bp.route('/provider_verification')
@login_required
@role_required('provider')
def provider_verification():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT name, email, profile_photo, description, verification_status, id_proof_image, business_name, phone, id_proof_number, address FROM users WHERE id = %s", (provider_id,))
    provider = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) AS total_services FROM services WHERE provider_id = %s", (provider_id,))
    total_services = cur.fetchone()['total_services']
    
    cur.execute("SELECT COUNT(*) AS notification_count FROM notifications WHERE provider_id = %s AND is_read = 0", (provider_id,))
    notification_count = cur.fetchone()['notification_count']
    
    conn.close()
    
    provider_name = provider.get("name") if provider else "Provider"
    profile_photo = (provider.get("profile_photo") if provider else None) or "default.png"
    provider_description = (provider.get("description") if provider else None)
    verification_status = (provider.get("verification_status") if provider else "Unverified") or "Unverified"

    # Verification Progress Logic
    is_profile_complete = bool(provider_name and provider_description and profile_photo != 'default.png')
    is_services_added = total_services > 0
    is_docs_uploaded = bool(provider.get('id_proof_image'))
    is_verified = (verification_status == 'Verified')
    
    return render_template("provider_verification.html", 
                           provider=provider,
                           provider_name=provider_name, 
                           profile_photo=profile_photo, 
                           notification_count=notification_count,
                           verification_status=verification_status,
                           is_profile_complete=is_profile_complete,
                           is_services_added=is_services_added,
                           is_docs_uploaded=is_docs_uploaded,
                           is_verified=is_verified)

@provider_bp.route('/provider_profile')
@login_required
@role_required('provider')
def provider_profile():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, email, profile_photo, description FROM users WHERE id = %s", (provider_id,))
    provider = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) AS notification_count FROM notifications WHERE provider_id = %s AND is_read = 0", (provider_id,))
    notification_count = cur.fetchone()['notification_count']
    
    conn.close()
    
    if not provider:
        flash("Provider details not found.", "danger")
        return redirect(url_for('provider.provider_dashboard'))

    return render_template("provider_profile.html", 
                           provider_name=provider['name'], 
                           email=provider['email'],
                           profile_photo=provider.get("profile_photo") or "default.png", 
                           provider_description=provider.get("description") or "No description added.",
                           notification_count=notification_count)

@provider_bp.route('/provider_services')
@login_required
@role_required('provider')
def provider_services():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM services WHERE provider_id = %s", (provider_id,))
    services = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS notification_count FROM notifications WHERE provider_id = %s AND is_read = 0", (provider_id,))
    notification_count = cur.fetchone()['notification_count']
    conn.close()
    return render_template('provider_services.html', services=services, notification_count=notification_count)

@provider_bp.route('/add_service', methods=['POST'])
@login_required
@role_required('provider')
def add_service():
    service_name = request.form['service_name']
    location = request.form['location']
    cost = request.form['cost']
    provider_id = session['user_id']
    
    conn = get_db_connection()
    cur = conn.cursor()
    

    cur.execute("INSERT INTO services (provider_id, service_name, location, cost, status) VALUES (%s, %s, %s, %s, 'Pending')", 
                (provider_id, service_name, location, cost))
    conn.commit()
    conn.close()
    flash("Service added successfully. Waiting for admin approval.", "success")
    return redirect(url_for('provider.provider_services'))
@provider_bp.route('/provider_report')
@login_required
@role_required('provider')
def provider_report():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    # ================= WEEKLY =================
    cur.execute("""
        SELECT COUNT(b.id) AS bookings, COUNT(DISTINCT b.user_id) AS users, IFNULL(SUM(b.amount), 0) AS revenue
        FROM bookings b JOIN services s ON b.service_id = s.id
        WHERE s.provider_id = %s AND b.status = 'Completed' AND YEARWEEK(b.booking_date, 1) = YEARWEEK(CURDATE(), 1)
    """, (provider_id,))
    weekly = cur.fetchone() or {'revenue': 0, 'bookings': 0, 'users': 0}

    # ================= MONTHLY =================
    cur.execute("""
        SELECT COUNT(b.id) AS bookings, COUNT(DISTINCT b.user_id) AS users, IFNULL(SUM(b.amount), 0) AS revenue
        FROM bookings b JOIN services s ON b.service_id = s.id
        WHERE s.provider_id = %s AND b.status = 'Completed' AND YEAR(b.booking_date) = YEAR(CURDATE()) AND MONTH(b.booking_date) = MONTH(CURDATE())
    """, (provider_id,))
    monthly = cur.fetchone() or {'revenue': 0, 'bookings': 0, 'users': 0}

    # ================= YEARLY =================
    cur.execute("""
        SELECT COUNT(b.id) AS bookings, COUNT(DISTINCT b.user_id) AS users, IFNULL(SUM(b.amount), 0) AS revenue
        FROM bookings b JOIN services s ON b.service_id = s.id
        WHERE s.provider_id = %s AND b.status = 'Completed' AND YEAR(b.booking_date) = YEAR(CURDATE())
    """, (provider_id,))
    yearly = cur.fetchone() or {'revenue': 0, 'bookings': 0, 'users': 0}

    cur.execute("""
        SELECT s.service_name, IFNULL(SUM(b.amount),0) AS total_earned
        FROM bookings b JOIN services s ON b.service_id = s.id
        WHERE s.provider_id = %s AND b.status = 'Completed' GROUP BY s.service_name
    """, (provider_id,))
    results = cur.fetchall()

    service_labels = [row['service_name'] for row in results] or ["No Data"]
    service_amounts = [float(row['total_earned']) for row in results] or [0]

    cur.execute("SELECT COUNT(*) AS notification_count FROM notifications WHERE provider_id = %s AND is_read = 0", (provider_id,))
    notification_count = cur.fetchone()['notification_count']
    conn.close()
    return render_template("provider_report.html", 
                           weekly_revenue=float(weekly['revenue']), weekly_bookings=weekly['bookings'], weekly_users=weekly['users'],
                           monthly_revenue=float(monthly['revenue']), monthly_bookings=monthly['bookings'], monthly_users=monthly['users'],
                           yearly_revenue=float(yearly['revenue']), yearly_bookings=yearly['bookings'], yearly_users=yearly['users'],
                           service_labels=service_labels, service_amounts=service_amounts,
                           notification_count=notification_count)

@provider_bp.route("/update_provider_profile", methods=["POST"])
@login_required
@role_required('provider')
def update_provider_profile():
    handle_profile_update(request, 'provider')
    return redirect(url_for("provider.provider_dashboard"))

@provider_bp.route("/remove_provider_photo", methods=["POST"])
@login_required
@role_required('provider')
def remove_provider_photo():
    handle_photo_removal()
    return redirect(url_for("provider.provider_dashboard"))

@provider_bp.route('/mark_completed/<int:booking_id>', methods=['POST'])
@login_required
@role_required('provider')
def mark_completed(booking_id):
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verify the booking belongs to a service owned by this provider
    cur.execute("""
        SELECT b.id, b.user_id, s.service_name 
        FROM bookings b 
        JOIN services s ON b.service_id = s.id 
        WHERE b.id = %s AND s.provider_id = %s
    """, (booking_id, provider_id))
    
    booking = cur.fetchone()
    if not booking:
        conn.close()
        flash("Unauthorized or booking not found.", "danger")
        return redirect(url_for('provider.provider_dashboard'))

    cur.execute("UPDATE bookings SET status='Completed' WHERE id=%s", (booking_id,))
    
    # Notify User
    msg = f"Your service '{booking['service_name']}' has been marked as completed by the provider. Please share your feedback!"
    cur.execute("INSERT INTO user_notifications (user_id, message) VALUES (%s, %s)", (booking['user_id'], msg))
    
    conn.commit()
    conn.close()
    flash("Booking marked as completed!", "success")
    return redirect(url_for('provider.provider_dashboard'))
@provider_bp.route('/provider_admin_action')
@login_required
@role_required('provider')
def provider_admin_action():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, message, is_read, created_at FROM notifications WHERE provider_id = %s ORDER BY created_at DESC", (provider_id,))
    notifications = cur.fetchall()
    
    # Mark as read when viewing this page
    cur.execute("UPDATE notifications SET is_read = 1 WHERE provider_id = %s", (provider_id,))
    conn.commit()
    
    # After marking as read, the count for THIS page view should technically be 0 (for the sidebar)
    # but since the update happened, we can just pass 0
    notification_count = 0
    
    conn.close()
    return render_template('provider_admin_action.html', notifications=notifications, notification_count=notification_count)
@provider_bp.route('/submit_verification', methods=['GET', 'POST'])
@login_required
@role_required('provider')
def submit_verification():
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        business_name = request.form['business_name']
        phone = request.form['phone']
        address = request.form['address']
        id_proof_number = request.form['id_proof_number']
        file = request.files.get('id_proof_image')
        
        filename = None
        if file and file.filename != "":
            from config import Config
            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"verify_{provider_id}.{ext}"
            upload_folder = os.path.join(Config.UPLOAD_FOLDER, "verification")
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
        cur.execute("""
            UPDATE users 
            SET business_name=%s, phone=%s, address=%s, id_proof_number=%s, id_proof_image=%s, 
                verification_status='Pending', verification_submitted_at=NOW()
            WHERE id=%s
        """, (business_name, phone, address, id_proof_number, filename, provider_id))
        
        conn.commit()
        conn.close()
        flash("✅ Verification details submitted successfully! Admin will review them shortly.", "success")
        return redirect(url_for('provider.provider_verification'))
    
    return redirect(url_for('provider.provider_verification'))
@provider_bp.route('/edit_service/<int:service_id>', methods=['GET', 'POST'])
@login_required
@role_required('provider')
def edit_service(service_id):
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verify owner
    cur.execute("SELECT * FROM services WHERE id = %s AND provider_id = %s", (service_id, provider_id))
    service = cur.fetchone()
    
    if not service:
        conn.close()
        flash("Unauthorized or service not found.", "danger")
        return redirect(url_for('provider.provider_services'))
    
    if request.method == 'POST':
        name = request.form['service_name']
        loc = request.form['location']
        cost = request.form['cost']
        
        # Reset to Pending after every edit to ensure admin review of changes
        cur.execute("""
            UPDATE services 
            SET service_name = %s, location = %s, cost = %s, status = 'Pending' 
            WHERE id = %s
        """, (name, loc, cost, service_id))
        
        conn.commit()
        conn.close()
        flash("Service updated successfully and sent for re-approval.", "success")
        return redirect(url_for('provider.provider_services'))
    
    cur.execute("SELECT COUNT(*) AS notification_count FROM notifications WHERE provider_id = %s AND is_read = 0", (provider_id,))
    notification_count = cur.fetchone()['notification_count']
    conn.close()
    return render_template('provider_edit_service.html', service=service, notification_count=notification_count)

@provider_bp.route('/delete_service/<int:service_id>')
@login_required
@role_required('provider')
def delete_service(service_id):
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verify owner
    cur.execute("SELECT id FROM services WHERE id = %s AND provider_id = %s", (service_id, provider_id))
    if not cur.fetchone():
        conn.close()
        flash("Unauthorized or service not found.", "danger")
        return redirect(url_for('provider.provider_services'))
        
    # Check for active bookings before deletion (soft constraint or delete cascade?)
    cur.execute("SELECT COUNT(*) as count FROM bookings WHERE service_id = %s AND status = 'Confirmed'", (service_id,))
    if cur.fetchone()['count'] > 0:
        conn.close()
        flash("Cannot delete service with active confirmed bookings.", "warning")
        return redirect(url_for('provider.provider_services'))

    cur.execute("DELETE FROM services WHERE id = %s", (service_id,))
    conn.commit()
    conn.close()
    flash("Service deleted successfully.", "success")
    return redirect(url_for('provider.provider_services'))
@provider_bp.route('/provider_cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
@role_required('provider')
def provider_cancel_booking(booking_id):
    provider_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verify ownership
    cur.execute(\"\"\"
        SELECT b.id, b.user_id, s.service_name, b.booking_date, b.time_slot 
        FROM bookings b JOIN services s ON b.service_id = s.id 
        WHERE b.id = %s AND s.provider_id = %s
    \"\"\", (booking_id, provider_id))
    
    booking = cur.fetchone()
    if not booking:
        conn.close()
        flash(\"Unauthorized or booking not found.\", \"danger\")
        return redirect(url_for('provider.provider_dashboard'))

    cur.execute(\"UPDATE bookings SET status = 'Cancelled' WHERE id = %s\", (booking_id,))
    
    # Notify User
    msg = f\"❌ Your booking for {booking['service_name']} on {booking['booking_date']} at {booking['time_slot']} has been CANCELLED by the provider.\"
    cur.execute(\"INSERT INTO user_notifications (user_id, message) VALUES (%s, %s)\", (booking['user_id'], msg))
    
    conn.commit()
    conn.close()
    flash(\"Booking cancelled successfully.\", \"success\")
    return redirect(url_for('provider.provider_dashboard'))
