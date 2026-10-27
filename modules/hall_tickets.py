from datetime import date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required, role_required
from database import (
    get_exam, get_exams, get_classes_list,
    get_exam_students_for_tickets, set_exam_seating,
    auto_assign_seating, get_exam_seating_summary,
    clear_exam_seating
)

hall_tickets_bp = Blueprint("hall_tickets", __name__,
                            url_prefix="/hall-tickets")


@hall_tickets_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    class_name = request.args.get("class", "").strip()
    exams_raw = get_exams(class_name or None)

    exams = []
    for e in exams_raw:
        exams.append({
            "id": e[0], "name": e[1], "class_name": e[2],
            "exam_date": e[3], "subjects": e[4] or [],
            "max_marks": e[5]
        })

    return render_template("hall_tickets/index.html",
                           exams=exams,
                           classes=get_classes_list(),
                           selected_class=class_name)


@hall_tickets_bp.route("/<int:exam_id>")
@login_required
@role_required("super_admin", "admin")
def manage(exam_id):
    exam_raw = get_exam(exam_id)
    if not exam_raw:
        abort(404)

    exam = {
        "id": exam_raw[0], "name": exam_raw[1],
        "class_name": exam_raw[2], "exam_date": exam_raw[3],
        "subjects": exam_raw[4] or [], "max_marks": exam_raw[5]
    }

    students = get_exam_students_for_tickets(exam_id)
    seating_summary = get_exam_seating_summary(exam_id)
    total_set = sum(r["count"] for r in seating_summary)

    return render_template("hall_tickets/manage.html",
                           exam=exam, students=students,
                           seating_summary=seating_summary,
                           total_set=total_set)


@hall_tickets_bp.route("/<int:exam_id>/auto-seat", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def auto_seat(exam_id):
    exam = get_exam(exam_id)
    if not exam:
        abort(404)

    room_start = request.form.get("room_start", "101").strip()
    per_room = int(request.form.get("per_room") or 30)

    n = auto_assign_seating(exam_id, room_no=room_start,
                            students_per_room=per_room)
    flash(f"{n} students ko auto-seat assign ho gaye", "success")
    return redirect(url_for("hall_tickets.manage", exam_id=exam_id))


@hall_tickets_bp.route("/<int:exam_id>/clear", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def clear_seating(exam_id):
    n = clear_exam_seating(exam_id)
    flash(f"{n} seating records delete ho gaye", "success")
    return redirect(url_for("hall_tickets.manage", exam_id=exam_id))


@hall_tickets_bp.route("/<int:exam_id>/set", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def set_seat(exam_id):
    student_id = request.form.get("student_id", type=int)
    room = request.form.get("room_no", "").strip()
    seat = request.form.get("seat_no", "").strip()

    if not student_id:
        flash("Invalid student", "error")
        return redirect(url_for("hall_tickets.manage", exam_id=exam_id))

    set_exam_seating(exam_id, student_id, room, seat)
    return redirect(url_for("hall_tickets.manage", exam_id=exam_id))


# ---------- Preview / Print ----------
@hall_tickets_bp.route("/<int:exam_id>/preview")
@login_required
@role_required("super_admin", "admin")
def preview(exam_id):
    exam_raw = get_exam(exam_id)
    if not exam_raw:
        abort(404)

    exam = {
        "id": exam_raw[0], "name": exam_raw[1],
        "class_name": exam_raw[2], "exam_date": exam_raw[3],
        "subjects": exam_raw[4] or [], "max_marks": exam_raw[5]
    }

    students = get_exam_students_for_tickets(exam_id)

    # Optional: filter by student
    student_id = request.args.get("student_id", type=int)
    if student_id:
        students = [s for s in students if s["id"] == student_id]

    return render_template("hall_tickets/print.html",
                           exam=exam, students=students,
                           school=None)  # school from context_processor


@hall_tickets_bp.route("/student/<int:student_id>/<int:exam_id>")
@login_required
@role_required("super_admin", "admin")
def single_ticket(student_id, exam_id):
    return redirect(url_for("hall_tickets.preview", exam_id=exam_id,
                            student_id=student_id))
