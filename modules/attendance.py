from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session
)
from modules.auth import login_required
from database import (
    get_attendance_for_date, mark_attendance, bulk_mark_attendance,
    class_attendance_today, get_classes_list, get_student,
    get_attendance_summary, get_attendance_calendar
)

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")

@attendance_bp.route("/")
@login_required
def index():
    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()
    date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")

    rows = []
    summary = None
    if class_name:
        raw = get_attendance_for_date(class_name, section, date)
        rows = [
            {"id": r[0], "name": r[1], "roll": r[2],
             "class_name": r[3], "section": r[4], "status": r[5]}
            for r in raw
        ]
        summary = class_attendance_today(class_name, section, date)

    return render_template(
        "attendance/index.html",
        classes=get_classes_list(),
        selected_class=class_name,
        selected_section=section,
        date=date,
        students=rows,
        summary=summary
    )

@attendance_bp.route("/mark", methods=["POST"])
@login_required
def mark():
    student_id = int(request.form["student_id"])
    date = request.form["date"]
    status = request.form["status"]
    class_name = request.form.get("class", "")
    section = request.form.get("section", "")
    mark_attendance(student_id, date, status, session["admin_id"])
    return redirect(url_for(
        "attendance.index",
        **{"class": class_name, "section": section, "date": date}
    ))

@attendance_bp.route("/mark-all", methods=["POST"])
@login_required
def mark_all():
    class_name = request.form["class"]
    section = request.form.get("section", "")
    date = request.form["date"]
    status = request.form["status"]
    bulk_mark_attendance(class_name, section, date, status, session["admin_id"])
    flash(f"Poori class ko '{status}' mark kar diya", "success")
    return redirect(url_for(
        "attendance.index",
        **{"class": class_name, "section": section, "date": date}
    ))

@attendance_bp.route("/student/<int:student_id>")
@login_required
def student_attendance(student_id):
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    summary = get_attendance_summary(student_id, month)
    calendar = get_attendance_calendar(student_id, month)
    row = get_student(student_id)
    if not row:
        return redirect(url_for("students.list_students"))
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))
    return render_template(
        "attendance/student.html",
        student=student,
        summary=summary,
        calendar=calendar,
        month=month
    )
