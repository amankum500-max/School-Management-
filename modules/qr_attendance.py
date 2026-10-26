from datetime import date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify
)
from modules.auth import login_required
from database import (
    get_student_by_qr_data, get_today_attendance_status,
    mark_attendance, get_class_students_for_qr,
    get_todays_attendance_summary, get_classes_list
)

qr_attendance_bp = Blueprint("qr_attendance", __name__, url_prefix="/qr-attendance")

@qr_attendance_bp.route("/scan")
@login_required
def scan():
    """Scanner page — camera se QR scan"""
    today = date.today().isoformat()
    summary = get_todays_attendance_summary(today)
    return render_template("qr_attendance/scan.html",
                           today=today, summary=summary)

@qr_attendance_bp.route("/mark", methods=["POST"])
@login_required
def mark():
    """AJAX endpoint — QR decoded data se attendance mark"""
    data = request.json or {}
    qr_text = data.get("qr_text", "").strip()
    date_str = data.get("date") or date.today().isoformat()
    status = data.get("status", "present")

    if not qr_text:
        return jsonify({"ok": False, "error": "QR data empty"}), 400

    if status not in ["present", "absent", "late", "leave"]:
        return jsonify({"ok": False, "error": "Invalid status"}), 400

    student = get_student_by_qr_data(qr_text)
    if not student:
        return jsonify({
            "ok": False,
            "error": "Student nahi mila — QR invalid ya student inactive"
        }), 404

    # Duplicate check
    existing = get_today_attendance_status(student["id"], date_str)
    already = existing is not None

    # Mark (upsert)
    mark_attendance(student["id"], date_str, status, session["admin_id"])

    summary = get_todays_attendance_summary(date_str)

    return jsonify({
        "ok": True,
        "student": {
            "id": student["id"],
            "name": student["name"],
            "roll": student["roll_no"],
            "class_name": student["class_name"],
            "section": student["section"]
        },
        "status": status,
        "already_marked": already,
        "previous_status": existing,
        "summary": summary
    })

@qr_attendance_bp.route("/bulk-print")
@login_required
def bulk_print():
    """Class ke saare QRs ek page pe — print/laminate karo"""
    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    students = []
    if class_name:
        students = get_class_students_for_qr(class_name, section or None)

    return render_template("qr_attendance/bulk_print.html",
                           students=students,
                           classes=get_classes_list(),
                           selected_class=class_name,
                           selected_section=section)

@qr_attendance_bp.route("/summary")
@login_required
def summary_api():
    """Live summary — dashboard/scan page auto-refresh"""
    today = request.args.get("date") or date.today().isoformat()
    return jsonify(get_todays_attendance_summary(today))
