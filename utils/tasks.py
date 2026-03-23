from datetime import datetime, timedelta
import pytz
import pymysql
from utils import get_db_connection

def auto_complete_past_bookings():
    """Automatically mark past bookings as Completed by comparing time slots."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST)
        today = now.date()
        
        # 1. Complete all confirmed bookings from strictly previous days
        cur.execute("UPDATE bookings SET status='Completed' WHERE status='Confirmed' AND booking_date < %s", (today,))
        
        # 2. Check today's bookings against their time slots
        cur.execute("""
            SELECT b.id, b.time_slot, b.user_id, s.provider_id, s.service_name 
            FROM bookings b 
            JOIN services s ON b.service_id = s.id
            WHERE b.status='Confirmed' AND b.booking_date = %s
        """, (today,))
        today_bookings = cur.fetchall()
        
        for b in today_bookings:
            try:
                # Flexible slot format handling
                slot = b['time_slot'].lower().replace(' to ', ' - ')
                parts = slot.split('-')
                if len(parts) != 2: continue
                
                end_time_str = parts[1].strip()
                parsed_end_time = None
                
                # Robust parsing
                for fmt in ["%I:%M %p", "%I %p", "%H:%M", "%H"]:
                    try:
                        parsed_end_time = datetime.strptime(end_time_str, fmt).time()
                        break
                    except ValueError:
                        continue
                
                if parsed_end_time and now.time() > parsed_end_time:
                    cur.execute("UPDATE bookings SET status='Completed' WHERE id = %s", (b['id'],))
                    
                    # Notify both parties
                    msg_user = f"Your service '{b['service_name']}' has been marked as completed. Please share your feedback!"
                    msg_provider = f"Booking for '{b['service_name']}' (ID: {b['id']}) has been marked as completed."
                    
                    cur.execute("INSERT INTO user_notifications (user_id, message) VALUES (%s, %s)", (b['user_id'], msg_user))
                    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", (b['provider_id'], msg_provider))
            except Exception as e:
                print(f"Error parsing slot for booking {b['id']}: {e}")
                continue
                
        conn.commit()
    except Exception as e:
        print(f"Error in auto_complete_past_bookings: {e}")
    finally:
        if conn:
            conn.close()

def send_booking_reminders():
    """Send booking reminders for upcoming slots within the next hour."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST)
        
        # Fetch today's unsent reminders for confirmed bookings
        cur.execute("""
            SELECT b.id, b.user_id, s.provider_id, s.service_name, b.booking_date, b.time_slot
            FROM bookings b JOIN services s ON b.service_id = s.id
            WHERE b.reminder_sent = 0 AND b.booking_date = %s AND b.status = 'Confirmed'
        """, (now.date(),))
        
        bookings = cur.fetchall()
        for b in bookings:
            try:
                slot = b['time_slot'].lower().replace(' to ', ' - ')
                start_time_str = slot.split('-')[0].strip()
                
                parsed_time = None
                for fmt in ["%I:%M %p", "%I %p", "%H:%M", "%H"]:
                    try:
                        # Handle cases like "9 am" which strptime might fail on without :00
                        t_str = start_time_str
                        if 'am' in t_str or 'pm' in t_str:
                             if ':' not in t_str:
                                 time_part = "".join([c for c in t_str if c.isdigit()])
                                 meridiem = "am" if "am" in t_str else "pm"
                                 t_str = f"{time_part}:00 {meridiem}"
                        elif ':' not in t_str:
                            t_str += ":00"
                            
                        parsed_time = datetime.strptime(t_str, fmt).time()
                        break
                    except ValueError:
                        continue
                
                if not parsed_time:
                    continue

                booking_time = IST.localize(datetime.combine(now.date(), parsed_time))
                
                # Send reminder if booking is within [now - 1hr, now + 3hrs]
                if (now - timedelta(hours=1)) <= booking_time <= (now + timedelta(hours=3)):
                    message = f"Reminder: Service '{b['service_name']}' is scheduled for today at {b['time_slot']}."
                    
                    cur.execute("INSERT INTO user_notifications (user_id, message) VALUES (%s, %s)", (b['user_id'], message))
                    cur.execute("INSERT INTO notifications (provider_id, message) VALUES (%s, %s)", (b['provider_id'], message))
                    cur.execute("UPDATE bookings SET reminder_sent = 1 WHERE id = %s", (b['id'],))
            except Exception as e:
                print(f"Error processing reminder for booking {b.get('id')}: {e}")
        
        conn.commit()
    except Exception as e:
        print(f"Error in send_booking_reminders: {e}")
    finally:
        if conn:
            conn.close()
