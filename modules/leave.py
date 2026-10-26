from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    get_leave_types, get_or_init_leave_balance, count_working_days,
    create_leave_application, get_leave_applications,
    get_leave_application, approve_leave, reject_leave, cancel_leave,
    get_pending_leave_count, get_staff_leave_summary,
    get_staff, get_staff_list
)

leave_bp = Blueprint("leave", __name__, url_prefix="/leave")

# ---------- Admin side ----------
@leave_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    status = request.args.get("status", "pending")
    staff_id = request.args.get("staff_id", type=int)

    applications = get_leave_applications(
        status=status or None,
        staff_id=staff_id,
        limit=100
    )
    pending_count = get_pending_leave_count()
    staff_list = get_staff_list()

    return render_template("leave/index.html",
                           applications=applications,
                           selected_status=status,
                           selected_staff=staff_id,
                           pending_count=pending_count,
                           staff_list=staff_list)

@leave_bp.route("/<int:lid>")
@login_required
@role_required("super_admin", "admin")
def detail(lid):
    app = get_leave_application(lid)
    if not app:
        abort(404)
    return render_template("leave/detail.html", app=app)

@leave_bp.route("/<int:lid>/approve", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def approve(lid):
    note = request.form.get("admin_note", "").strip()
    result = approve_leave(lid, session["admin_id"], note)
    if result and result.get("ok"):
        flash("Leave approved + attendance marked", "success")
    else:
        flash(f"Approve fail: {result.get('error', 'already reviewed') if result else 'not found'}",
              "error")
    return redirect(url_for("leave.index"))

@leave_bp.route("/<int:lid>/reject", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def reject(lid):
    note = request.form.get("admin_note", "").strip()
    if reject_leave(lid, session["admin_id"], note):
        flash("Leave rejected", "success")
    else:
        flash("Reject fail — already reviewed", "error")
    return redirect(url_for("leave.index"))

# ---------- Apply (admin adds on behalf of staff) ----------
@leave_bp.route("/apply", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def apply():
    leave_types = get_leave_types()

    if request.method == "POST":
        staff_id = request.form.get("staff_id", type=int)
        leave_type_id = request.form.get("leave_type_id", type=int)
        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")
        reason = request.form.get("reason", "")

        if not all([staff_id, leave_type_id, from_date, to_date]):
            flash("Sab fields zaroori hain", "error")
            return redirect(url_for("leave.apply"))

        try:
            result = create_leave_application(
                staff_id, leave_type_id, from_date, to_date, reason
            )
            flash(f"Leave application submit ho gayi ({result['days']} days)", "success")
            return redirect(url_for("leave.detail", lid=result["id"]))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("leave.apply"))

    staff_list = get_staff_list()
    return render_template("leave/apply.html",
                           leave_types=leave_types,
                           staff_list=staff_list,
                           today=date.today().isoformat())

# ---------- Staff profile integration ----------
@leave_bp.route("/staff/<int:staff_id>")
@login_required
def staff_leave(staff_id):
    m = get_staff(staff_id)
    if not m:
        abort(404)
    year = datetime.now().year
    summary = get_staff_leave_summary(staff_id, year)
    history = get_leave_applications_for_staff(staff_id, limit=30)
    return render_template("leave/staff_view.html",
                           m=m, summary=summary, history=history)
