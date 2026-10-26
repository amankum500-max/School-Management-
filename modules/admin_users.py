from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    get_all_admins, get_admin_by_id, create_admin_user,
    update_admin_user, delete_admin_user, reset_admin_password,
    get_audit_logs, log_audit, ADMIN_ROLES
)

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/admin-users")

@admin_users_bp.route("/")
@login_required
@role_required("super_admin")
def index():
    admins = get_all_admins()
    return render_template("admin_users/index.html",
                           admins=admins, roles=ADMIN_ROLES,
                           current_id=session["admin_id"])

@admin_users_bp.route("/add", methods=["POST"])
@login_required
@role_required("super_admin")
def add():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "").strip()
    role = request.form.get("role", "admin")

    if not username or len(password) < 6 or role not in ADMIN_ROLES:
        flash("Username, 6+ password, valid role zaroori hain", "error")
        return redirect(url_for("admin_users.index"))

    try:
        new_id = create_admin_user(username, password, full_name, role)
        log_audit(session["admin_id"], session["admin_username"],
                  "create_admin", "POST", "/admin-users/add",
                  entity=f"admin:{new_id}",
                  details=f"username={username}, role={role}",
                  ip=request.remote_addr)
        flash("Admin user create ho gaya", "success")
    except Exception:
        flash("Username already taken ya kuch galat hua", "error")
    return redirect(url_for("admin_users.index"))

@admin_users_bp.route("/<int:aid>/edit", methods=["POST"])
@login_required
@role_required("super_admin")
def edit(aid):
    if aid == session["admin_id"]:
        flash("Apni hi profile yahan se change nahi kar sakte — Profile page use karo", "error")
        return redirect(url_for("admin_users.index"))

    full_name = request.form.get("full_name", "").strip()
    role = request.form.get("role", "admin")
    is_active = request.form.get("is_active") == "on"

    if role not in ADMIN_ROLES:
        flash("Invalid role", "error")
        return redirect(url_for("admin_users.index"))

    update_admin_user(aid, full_name, role, is_active)
    log_audit(session["admin_id"], session["admin_username"],
              "update_admin", "POST", f"/admin-users/{aid}/edit",
              entity=f"admin:{aid}",
              details=f"role={role}, active={is_active}",
              ip=request.remote_addr)
    flash("Admin update ho gaya", "success")
    return redirect(url_for("admin_users.index"))

@admin_users_bp.route("/<int:aid>/delete", methods=["POST"])
@login_required
@role_required("super_admin")
def remove(aid):
    if aid == session["admin_id"]:
        flash("Apne aap ko delete nahi kar sakte", "error")
        return redirect(url_for("admin_users.index"))

    target = get_admin_by_id(aid)
    delete_admin_user(aid)
    log_audit(session["admin_id"], session["admin_username"],
              "delete_admin", "POST", f"/admin-users/{aid}/delete",
              entity=f"admin:{aid}",
              details=f"deleted {target['username'] if target else '?'}",
              ip=request.remote_addr)
    flash("Admin user delete ho gaya", "success")
    return redirect(url_for("admin_users.index"))

@admin_users_bp.route("/<int:aid>/reset", methods=["POST"])
@login_required
@role_required("super_admin")
def reset(aid):
    new_password = request.form.get("new_password", "")
    if len(new_password) < 6:
        flash("Kam se kam 6 characters", "error")
        return redirect(url_for("admin_users.index"))
    reset_admin_password(aid, new_password)
    log_audit(session["admin_id"], session["admin_username"],
              "reset_password", "POST", f"/admin-users/{aid}/reset",
              entity=f"admin:{aid}", ip=request.remote_addr)
    flash("Password reset ho gaya", "success")
    return redirect(url_for("admin_users.index"))

# ---------- Audit Logs Viewer ----------
@admin_users_bp.route("/audit")
@login_required
@role_required("super_admin", "admin")
def audit():
    action = request.args.get("action", "").strip()
    admin_id = request.args.get("admin_id", type=int)
    logs = get_audit_logs(admin_id=admin_id, action=action or None, limit=300)
    admins = get_all_admins()
    return render_template("admin_users/audit.html",
                           logs=logs, admins=admins,
                           selected_action=action, selected_admin=admin_id)
