from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash
)
# Database se zaroori functions import kar rahe hain
from database import (
    verify_admin, get_admin, update_admin_profile, 
    change_admin_password, update_admin_last_login, log_audit
)

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "admin_id" not in session:
                return redirect(url_for("auth.login"))
            if session.get("admin_role") not in allowed_roles:
                flash("Aapko is page ka access nahi hai", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "admin_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # Ye function database.py se aa raha hai
        admin = verify_admin(username, password)
        
        if admin:
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["full_name"] or admin["username"]
            session["admin_username"] = admin["username"]
            session["admin_role"] = admin["role"]

            # last_login + audit
            update_admin_last_login(admin["id"])
            log_audit(admin["id"], admin["username"], "login", "POST", "/login")

            return redirect(url_for("dashboard"))
        flash("Galat username ya password", "error")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    admin = get_admin(session["admin_id"])
    if not admin:
        flash("Admin record not found", "error")
        return redirect(url_for("auth.logout"))

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "profile":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip()
            if not username:
                flash("Username khaali nahi ho sakta", "error")
            else:
                try:
                    update_admin_profile(admin["id"], full_name, username)
                    session["admin_name"] = full_name or username
                    flash("Profile update ho gaya", "success")
                except Exception:
                    flash("Username already taken", "error")
            return redirect(url_for("auth.profile"))

        elif action == "password":
            old = request.form.get("old_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if len(new) < 6:
                flash("Naya password kam se kam 6 characters ka hona chahiye", "error")
            elif new != confirm:
                flash("New password aur confirm match nahi kar rahe", "error")
            elif not change_admin_password(admin["id"], old, new):
                flash("Purana password galat hai", "error")
            else:
                flash("Password change ho gaya", "success")
            return redirect(url_for("auth.profile"))

    return render_template("profile.html", admin=admin)
