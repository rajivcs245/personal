import os
from flask import flash, session, redirect, url_for
from . import get_db_connection

def handle_profile_update(request, role):
    """
    Common logic for updating user profiles across different roles.
    Includes handling name, description, and profile photo uploads.
    """
    name = request.form.get("name")
    description = request.form.get("description")
    file = request.files.get("photo")
    user_id = session.get("user_id")

    if not user_id:
        flash("Unauthorized access!", "danger")
        return False

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if file and file.filename != "":
            # Basic file type verification (can be expanded)
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            ext = file.filename.rsplit(".", 1)[1].lower()
            
            if ext not in allowed_extensions:
                flash("Invalid file type! Please upload an image.", "danger")
                return False

            from config import Config
            filename = f"{role}_{user_id}.{ext}"
            upload_folder = os.path.join(Config.UPLOAD_FOLDER, "profiles")
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            cur.execute("UPDATE users SET name=%s, description=%s, profile_photo=%s WHERE id=%s", 
                        (name, description, filename, user_id))
        else:
            cur.execute("UPDATE users SET name=%s, description=%s WHERE id=%s", 
                        (name, description, user_id))
        
        conn.commit()
        flash("✅ Profile updated successfully!", "success")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating profile: {e}")
        flash("Failed to update profile. Please try again.", "danger")
        return False
    finally:
        conn.close()

def handle_photo_removal():
    """Removes profile photo and resets to default.png."""
    user_id = session.get("user_id")
    if not user_id:
        return False

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT profile_photo FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
        
        if user and user['profile_photo'] != 'default.png':
            from config import Config
            file_path = os.path.join(Config.UPLOAD_FOLDER, "profiles", user['profile_photo'])
            if os.path.exists(file_path):
                os.remove(file_path)
                
        cur.execute("UPDATE users SET profile_photo=%s WHERE id=%s", ("default.png", user_id))
        conn.commit()
        flash("Profile photo removed successfully!", "success")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error removing photo: {e}")
        flash("Failed to remove photo.", "danger")
        return False
    finally:
        conn.close()
