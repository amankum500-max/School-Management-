from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    create_staff, get_staff_list, get_staff,
    update_staff, delete_staff, get_classes_list
)

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")

ROLES = ["teacher", "principal", "admin", "accountant",
         "librarian", "driver", "helper", "other"]

def _parse_list(value):
    """comma-separated string → list, trim, filter empty"""
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]

@staff_bp.route("/")
@login_required
def index():
    search = request.args.get("q", "").strip()
    role = request.args.get("role", "").strip()
    members = get_staff_list(search or None, role or None)
    return render_template(
        "staff/index.html",
        members=members,
        search=search,
        selected_role=role,
        roles=ROLES
    )

@staff_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        data["subjects"] = _parse_list(data.get("subjects_raw", ""))
        data["classes"] = _parse_list(data.get("classes_raw", ""))
        if not data.get("name"):
            flash("Name zaroori hai", "error")
            return redirect(url_for("staff.add"))
        sid = create_staff(data)
        flash(f"Staff member add ho gaya (ID: {sid})", "success")
        return redirect(url_for("staff.view", staff_id=sid))
    return render_template("staff/form.html", member=None, mode="add",
                           roles=ROLES, classes=get_classes_list())

@staff_bp.route("/<int:staff_id>")
@login_required
def view(staff_id):
    m = get_staff(staff_id)
    if not m:
        abort(404)
    return render_template("staff/profile.html", m=m)

@staff_bp.route("/<int:staff_id>/edit", methods=["GET", "POST"])
@login_required
def edit(staff_id):
    m = get_staff(staff_id)
    if not m:
        abort(404)
    if request.method == "POST":
        data = request.form.to_dict()
        data["subjects"] = _parse_list(data.get("subjects_raw", ""))
        data["classes"] = _parse_list(data.get("classes_raw", ""))
        update_staff(staff_id, data)
        flash("Staff update ho gaya", "success")
        return redirect(url_for("staff.view", staff_id=staff_id))
    return render_template("staff/form.html", member=m, mode="edit",
                           roles=ROLES, classes=get_classes_list())

@staff_bp.route("/<int:staff_id>/delete", methods=["POST"])
@login_required
def remove(staff_id):
    delete_staff(staff_id)
    flash("Staff delete ho gaya", "success")
    return redirect(url_for("staff.index"))
