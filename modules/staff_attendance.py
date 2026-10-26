from datetime import date, datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    get_staff_attendance_for_date, mark_staff_attendance,
    bulk_mark_staff_attendance, delete_staff_attendance,
    get_staff_attendance_summary, get_staff_attendance_month_matrix,
    get_staff_attendance_for_salary, get_staff_attendance_today_summary,
    get_staff, get_staff_list
)

staff_att_bp = Blueprint("staff_attendance", __name__,
                          url_prefix="/staff-attendance")

STAFF_STATUSES = ["present", "absent", "half_day", "leave", "holiday"]

@staff_att_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    date_str = request.args.get("date") or date.today().isoformat()
    role = request.args.get("role", "").strip()

    staff = get_staff_attendance_for_date(date_str, role or None)
    summary = get_staff_attendance_today_summary(date_str)

    # Distinct roles for filter
    from database import get_staff_list
    all_staff = get_staff_list()
    roles = sorted(set(s["role"] for s in all_staff if s["role"]))

    return render_template("staff_attendance/index.html",
                           staff=staff, date=date_str,
                           summary=summary, roles=roles,
                           selected_role=role,
                           statuses=STAFF_STATUSES)

@staff_att_bp.route("/mark", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def mark():
    staff_id = request.form.get("staff_id", type=int)
    date_str = request.form.get("date")
    status = request.form.get("status")
    note = request.form.get("note", "")

    if not staff_id or not date_str or status not in STAFF_STATUSES:
        flash("Invalid data", "error")
        return redirect(url_for("staff_attendance.index", date=date_str))

    mark_staff_attendance(staff_id, date_str, status, session["admin_id"],
                           note=note or None)
    return redirect(url_for("staff_attendance.index", date=date_str))

@staff_att_bp.route("/mark-all", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def mark_all():
    date_str = request.form.get("date")
    status = request.form.get("status")
    role = request.form.get("role", "").strip()

    if status not in STAFF_STATUSES:
        flash("Invalid status", "error")
        return redirect(url_for("staff_attendance.index", date=date_str))

    # Get all active staff (filtered by role if provided)
    staff = get_staff_attendance_for_date(date_str, role or None)
    staff_ids = [s["id"] for s in staff]

    n = bulk_mark_staff_attendance(staff_ids, date_str, status, session["admin_id"])
    flash(f"{n} staff ko '{status}' mark kar diya", "success")
    return redirect(url_for("staff_attendance.index", date=date_str))

@staff_att_bp.route("/delete/<int:att_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete(att_id):
    date_str = request.form.get("date") or date.today().isoformat()
    delete_staff_attendance(att_id)
    flash("Attendance entry delete ho gayi", "success")
    return redirect(url_for("staff_attendance.index", date=date_str))

# ---------- Monthly matrix view ----------
@staff_att_bp.route("/monthly")
@login_required
@role_required("super_admin", "admin")
def monthly():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    data = get_staff_attendance_month_matrix(month)
    return render_template("staff_attendance/monthly.html",
                           month=month, data=data)

# ---------- Staff detail view ----------
@staff_att_bp.route("/staff/<int:staff_id>")
@login_required
@role_required("super_admin", "admin")
def staff_detail(staff_id):
    m = get_staff(staff_id)
    if not m:
        abort(404)

    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    summary = get_staff_attendance_summary(staff_id, month)
    deduction = get_staff_attendance_for_salary(staff_id, month)

    # Day-wise records for the month
    from supabase_client import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, status, check_in_time, check_out_time, note
        FROM staff_attendance
        WHERE staff_id=%s AND TO_CHAR(date, 'YYYY-MM')=%s
        ORDER BY date;
    """, (staff_id, month))
    records = [{"date": r[0], "status": r[1],
                "check_in": r[2], "check_out": r[3], "note": r[4]}
               for r in cur.fetchall()]
    cur.close()
    conn.close()

    return render_template("staff_attendance/staff_detail.html",
                           m=m, month=month, summary=summary,
                           deduction=deduction, records=records)
