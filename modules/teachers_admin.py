from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash
)
from modules.auth import login_required
from database import (
    create_teacher, get_all_teachers, delete_teacher,
    reset_teacher_password, get_staff_list
)

teachers_admin_bp = Blueprint("teachers_admin", __name__,
                              url_prefix="/teachers-admin")

@teachers_admin_bp.route("/")
@login_required
def index():
    teachers = get_all_teachers()
    staff_without_login = []
    existing_staff_ids = {t["staff_id"] for t in teachers}
    for s in get_staff_list():
        if s["status"] == "active" and s["id"] not in existing_staff_ids:
            staff_without_login.append(s)
    return render_template("teachers_admin/index.html",
                           teachers=teachers,
                           staff_without_login=staff_without_login)

@teachers_admin_bp.route("/add", methods=["POST"])
@login_required
def add():
    staff_id = request.form.get("staff_id", type=int)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not staff_id or not username or len(password) < 6:
        flash("Staff, username, aur 6+ char password zaroori", "error")
        return redirect(url_for("teachers_admin.index"))

    try:
        create_teacher(staff_id, username, password)
        flash("Teacher login ban gaya", "success")
    except Exception:
        flash("Username already taken ya kuch galat hua", "error")
    return redirect(url_for("teachers_admin.index"))

@teachers_admin_bp.route("/<int:tid>/delete", methods=["POST"])
@login_required
def remove(tid):
    delete_teacher(tid)
    flash("Teacher login delete ho gaya", "success")
    return redirect(url_for("teachers_admin.index"))

@teachers_admin_bp.route("/<int:tid>/reset", methods=["POST"])
@login_required
def reset(tid):
    new_pass = request.form.get("new_password", "")
    if len(new_pass) < 6:
        flash("Kam se kam 6 characters", "error")
        return redirect(url_for("teachers_admin.index"))
    reset_teacher_password(tid, new_pass)
    flash("Password reset ho gaya", "success")
    return redirect(url_for("teachers_admin.index"))
