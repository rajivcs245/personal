from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils import get_db_connection, login_required, role_required
from utils.profile import handle_profile_update, handle_photo_removal
import pytz
from datetime import datetime, date
import os

user_bp = Blueprint('user', __name__)

@user_bp.route('/user_dashboard')
@login_required
@role_required('user')
def user_dashboard():
    user_id = session['user_id']
    search_query = request.args.get('q', '').strip()
    location_filter = request.args.get('location', '').strip()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT name, email, profile_photo, description FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    
    if not user:
        conn.close()
        flash("User not found!", "danger")
        return redirect(url_for("auth.login"))

    # Fetch unique locations for the filter dropdown
    cur.execute("SELECT DISTINCT location FROM services WHERE status='Approved'")
    locations = [row['location'] for row in cur.fetchall()]

    # Base query with average rating
    query = """
        SELECT s.*, u.name AS provider_name, 
               IFNULL((SELECT AVG(rating) FROM reviews WHERE provider_id = s.provider_id), 0) AS avg_rating,
               IFNULL((SELECT COUNT(*) FROM reviews WHERE provider_id = s.provider_id), 0) AS review_count
        FROM services s 
        JOIN users u ON s.provider_id = u.id 
        WHERE s.status='Approved'
    """
    params = []

    if search_query:
        query += " AND (s.service_name LIKE %s OR u.name LIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    
    if location_filter:
        query += " AND s.location = %s"
        params.append(location_filter)

    cur.execute(query, tuple(params))
    services = cur.fetchall()
    conn.close()

    return render_template("user_dashboard.html", 
                           services=services, 
                           locations=locations,
                           search_query=search_query,
                           selected_location=location_filter,
                           user_name=user["name"], 
                           profile_photo=user.get("profile_photo") or "default.png", 
                           user_description=user.get("description") or "No description added.")

@user_bp.route('/user_profile')
@login_required
@role_required('user')
def user_profile():
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, email, profile_photo, description FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    conn.close()
    
    return render_template("user_profile.html", 
                           user_name=user["name"], 
                           email=user["email"],
                           profile_photo=user.get("profile_photo") or "default.png", 
                           user_description=user.get("description") or "No description added.")

@user_bp.route('/booking/<int:service_id>', methods=['GET', 'POST'])
@login_required
@role_required('user')
def booking(service_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.id, s.service_name, s.location, s.cost, s.provider_id, u.name AS provider_name
        FROM services s JOIN users u ON s.provider_id = u.id WHERE s.id = %s
    """, (service_id,))
    service = cur.fetchone()

    if not service:
        conn.close()
        return "Service not found", 404

    ALL_SLOTS = [("09:00 AM", "11:00 AM"), ("11:00 AM", "01:00 PM"), ("02:00 PM", "04:00 PM"), ("04:00 PM", "06:00 PM")]

    if request.method == 'POST':
        booking_date = request.form['booking_date']
        time_slot = request.form['time_slot']
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST)
        
        try:
            b_date_obj = datetime.strptime(booking_date, "%Y-%m-%d").date()
            if b_date_obj == now.date():
                start_time_str = time_slot.split('-')[0].strip()
                start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
                if now.time() >= start_time:
                    conn.close()
                    return "This time slot has already passed.", 400
        except ValueError:
            pass

        cur.execute("""
            SELECT b.id FROM bookings b JOIN services s ON b.service_id = s.id
            WHERE s.provider_id = %s AND b.booking_date = %s AND b.time_slot = %s AND b.status != 'Cancelled'
        """, (service['provider_id'], booking_date, time_slot))

        if cur.fetchone():
            conn.close()
            return "This time slot is already booked for this provider.", 400

        cur.execute("""
            INSERT INTO bookings (user_id, service_id, provider_id, booking_date, time_slot, status, amount) 
            VALUES (%s, %s, %s, %s, %s, 'Confirmed', %s)
        """, (session['user_id'], service_id, service['provider_id'], booking_date, time_slot, service['cost']))
        
        booking_id = cur.lastrowid
        cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)",
                    (service['provider_id'], f"New booking received for {service['service_name']} on {booking_date} at {time_slot}"))
        
        # Immediate notification for the user
        cur.execute("INSERT INTO user_notifications (user_id, message) VALUES (%s, %s)",
                    (session['user_id'], f"Booking confirmed for {service['service_name']} on {booking_date} at {time_slot}"))
        
        conn.commit()
        conn.close()
        return render_template("booking_success.html", booking_ref=f"BK-{booking_id}", booking_date=booking_date, time_slot=time_slot, service_name=service['service_name'], cost=service['cost'])

    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST)
    today = now.date()
    selected_date = request.args.get('booking_date', today.isoformat())

    cur.execute("""
        SELECT b.time_slot FROM bookings b JOIN services s ON b.service_id = s.id
        WHERE s.provider_id = %s AND b.booking_date = %s AND b.status != 'Cancelled'
    """, (service['provider_id'], selected_date))
    booked_slots = {row['time_slot'] for row in cur.fetchall()}

    available_slots = []
    try:
        current_sel_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        current_sel_date_obj = today

    for start, end in ALL_SLOTS:
        start_time = datetime.strptime(start, "%I:%M %p").time()
        slot_label = f"{start} - {end}"
        if current_sel_date_obj == today and now.time() >= start_time:
            continue
        if slot_label not in booked_slots:
            available_slots.append(slot_label)

    conn.close()
    return render_template("booking.html", service=service, available_slots=available_slots, selected_date=selected_date, today=today.isoformat())

@user_bp.route('/my_transactions')
@login_required
@role_required('user')
def my_transactions():
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, s.service_name, u.name AS provider_name, b.booking_date, b.time_slot, b.amount, b.status
        FROM bookings b JOIN services s ON b.service_id = s.id JOIN users u ON s.provider_id = u.id
        WHERE b.user_id = %s ORDER BY b.booking_date DESC
    """, (user_id,))
    bookings = cur.fetchall()
    conn.close()
    return render_template('my_transactions.html', bookings=bookings)

@user_bp.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
@role_required('user')
def cancel_booking(booking_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.booking_date, b.time_slot, s.service_name, s.provider_id
        FROM bookings b JOIN services s ON b.service_id = s.id WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, user_id))
    booking = cur.fetchone()
    if not booking:
        conn.close()
        return "Booking not found or not authorized", 404
    cur.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = %s", (booking_id,))
    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)",
                (booking["provider_id"], f"Booking Cancelled: {booking['service_name']} on {booking['booking_date']} at {booking['time_slot']}"))
    conn.commit()
    conn.close()
    return redirect(url_for('user.my_transactions'))
@user_bp.route('/user_report')
@login_required
@role_required('user')
def user_report():
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS weekly_spending
        FROM bookings WHERE user_id = %s AND status = 'Completed' AND YEARWEEK(booking_date, 1) = YEARWEEK(CURDATE(), 1)
    """, (user_id,))
    row = cur.fetchone()
    weekly_spending = row['weekly_spending'] if row else 0

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS monthly_spending
        FROM bookings WHERE user_id = %s AND status = 'Completed' AND YEAR(booking_date) = YEAR(CURDATE()) AND MONTH(booking_date) = MONTH(CURDATE())
    """, (user_id,))
    row = cur.fetchone()
    monthly_spending = row['monthly_spending'] if row else 0

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS yearly_spending
        FROM bookings WHERE user_id = %s AND status = 'Completed' AND YEAR(booking_date) = YEAR(CURDATE())
    """, (user_id,))
    row = cur.fetchone()
    yearly_spending = row['yearly_spending'] if row else 0

    cur.execute("""
        SELECT s.service_name, IFNULL(SUM(b.amount),0) AS total_spent
        FROM bookings b JOIN services s ON b.service_id = s.id
        WHERE b.user_id = %s AND b.status = 'Completed' GROUP BY s.service_name
    """, (user_id,))
    results = cur.fetchall()

    service_labels = [row['service_name'] for row in results] or ["No Data"]
    service_amounts = [float(row['total_spent']) for row in results] or [0]

    conn.close()
    return render_template("user_report.html", 
                           weekly_spending=float(weekly_spending), 
                           monthly_spending=float(monthly_spending),
                           yearly_spending=float(yearly_spending), 
                           service_labels=service_labels, 
                           service_amounts=service_amounts)

@user_bp.route("/update_profile", methods=["POST"])
@login_required
@role_required('user')
def update_profile():
    handle_profile_update(request, 'user')
    return redirect(url_for("user.user_dashboard"))

@user_bp.route("/remove_profile_photo", methods=["POST"])
@login_required
@role_required('user')
def remove_profile_photo():
    handle_photo_removal()
    return redirect(url_for("user.user_dashboard"))

@user_bp.route('/generate_bill/<int:booking_id>')
@login_required
@role_required('user')
def generate_bill(booking_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id AS booking_id, u.name AS user_name, s.service_name, s.cost, b.booking_date, b.time_slot
        FROM bookings b JOIN users u ON b.user_id = u.id JOIN services s ON b.service_id = s.id
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, user_id))
    bill = cur.fetchone()
    conn.close()
    if not bill:
        flash("Bill not found or unauthorized.", "danger")
        return redirect(url_for('user.my_transactions'))
    return render_template("bill.html", bill=bill)

@user_bp.route('/notifications')
@login_required
@role_required('user')
def user_notifications():
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Mark as read
    cur.execute("UPDATE user_notifications SET is_read = 1 WHERE user_id = %s", (user_id,))
    conn.commit()
    
    # Fetch all
    cur.execute("SELECT message, created_at FROM user_notifications WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    notifications = cur.fetchall()
    conn.close()
    
    return render_template("user_notifications.html", notifications=notifications)

@user_bp.route('/submit_review', methods=['POST'])
@login_required
@role_required('user')
def submit_review():
    user_id = session['user_id']
    booking_id = request.form.get('booking_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    conn = get_db_connection()
    cur = conn.cursor()

    # Verify the booking exists, belongs to the user, and is marked 'Completed'
    cur.execute("""
        SELECT b.id, s.provider_id, b.status 
        FROM bookings b JOIN services s ON b.service_id = s.id 
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, user_id))
    booking = cur.fetchone()

    if not booking:
        conn.close()
        flash("Invalid booking reference.", "danger")
        return redirect(url_for('user.my_transactions'))
    
    if booking['status'] != 'Completed':
        conn.close()
        flash("You can only review completed services.", "warning")
        return redirect(url_for('user.my_transactions'))

    # Check if already reviewed
    cur.execute("SELECT id FROM reviews WHERE booking_id = %s", (booking_id,))
    if cur.fetchone():
        conn.close()
        flash("You have already reviewed this service.", "info")
        return redirect(url_for('user.my_transactions'))

    # Insert review
    cur.execute("""
        INSERT INTO reviews (booking_id, user_id, provider_id, rating, comment) 
        VALUES (%s, %s, %s, %s, %s)
    """, (booking_id, user_id, booking['provider_id'], rating, comment))
    
    conn.commit()
    conn.close()
    flash("⭐ Thank you for your feedback!", "success")
    return redirect(url_for('user.my_transactions'))
