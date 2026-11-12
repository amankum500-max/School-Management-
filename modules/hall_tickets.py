"""
Hall Ticket Module — Complete Routes
Place in project root. Register in app.py: from routes_hall_ticket import hall_ticket_bp
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from functools import wraps
import database as db
from datetime import datetime

hall_ticket_bp = Blueprint('hall_ticket', __name__, url_prefix='/hall-ticket')

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_id'):
            flash("Please login first", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────
# 1. LIST EXAMS (select exam to generate hall tickets)
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/')
@login_required
def index():
    class_name = request.args.get('class_name', '')
    exams = db.get_exams(class_name=class_name or None)
    classes = db.get_classes_list()
    # Build exam list with seating status
    exam_list = []
    for e in exams:
        exam_dict = {
            "id": e[0], "name": e[1], "class_name": e[2],
            "exam_date": e[3], "subjects": e[4] or [], "max_marks": e[5],
            "seated_count": 0, "total_students": 0,
        }
        try:
            summary = db.get_exam_seating_summary(e[0])
            exam_dict["seated_count"] = sum(r["student_count"] for r in summary)
            students = db.get_exam_students_for_tickets(e[0])
            exam_dict["total_students"] = len(students)
        except Exception:
            pass
        exam_list.append(exam_dict)
    return render_template('hall_ticket/index.html',
                           exams=exam_list, classes=classes,
                           selected_class=class_name)


# ─────────────────────────────────────────────────────────
# 2. SEATING MANAGEMENT (auto-assign / manual)
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/seating/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def seating(exam_id):
    exam = db.get_exam(exam_id)
    if not exam:
        flash("Exam not found", "danger")
        return redirect(url_for('hall_ticket.index'))

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'auto':
            capacity = int(request.form.get('room_capacity', 30) or 30)
            ok = db.auto_assign_seating(exam_id, room_capacity=capacity)
            flash("Seating auto-assigned successfully!" if ok else "Auto-assign failed", 
                  "success" if ok else "danger")
        elif action == 'clear':
            db.clear_exam_seating(exam_id)
            flash("All seating cleared", "info")
        elif action == 'manual':
            sid = request.form.get('student_id')
            room = request.form.get('room_no', '').strip()
            seat = request.form.get('seat_no', '').strip()
            if sid and room and seat:
                db.set_exam_seating(exam_id, int(sid), room, seat)
                flash("Seat assigned", "success")
            else:
                flash("Room and seat are required", "warning")
        return redirect(url_for('hall_ticket.seating', exam_id=exam_id))

    students = db.get_exam_students_for_tickets(exam_id)
    summary = db.get_exam_seating_summary(exam_id)
    return render_template('hall_ticket/seating.html',
                           exam={"id": exam[0], "name": exam[1],
                                 "class_name": exam[2], "exam_date": exam[3]},
                           students=students, summary=summary)


# ─────────────────────────────────────────────────────────
# 3. VIEW SINGLE HALL TICKET
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/view/<int:exam_id>/<int:student_id>')
@login_required
def view_ticket(exam_id, student_id):
    exam = db.get_exam(exam_id)
    student_row = db.get_student(student_id)
    if not exam or not student_row:
        abort(404)

    exam_dict = {"id": exam[0], "name": exam[1], "class_name": exam[2],
                 "exam_date": exam[3], "subjects": exam[4] or [],
                 "max_marks": exam[5]}
    student = {"id": student_row[0], "name": student_row[1],
               "roll_no": student_row[2], "class_name": student_row[3],
               "section": student_row[4], "parent_name": student_row[7],
               "parent_phone": student_row[8], "photo_url": student_row[13]}

    # Seating
    seating_info = {"room_no": "—", "seat_no": "—"}
    for s in db.get_exam_students_for_tickets(exam_id):
        if s["id"] == student_id:
            seating_info = {"room_no": s.get("room_no") or "—",
                            "seat_no": s.get("seat_no") or "—"}
            break

    settings = db.get_settings()
    return render_template('hall_ticket/ticket_single.html',
                           exam=exam_dict, student=student,
                           seating=seating_info, settings=settings)


# ─────────────────────────────────────────────────────────
# 4. BULK PRINT (all students of an exam)
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/bulk/<int:exam_id>')
@login_required
def bulk_print(exam_id):
    exam = db.get_exam(exam_id)
    if not exam:
        abort(404)
    exam_dict = {"id": exam[0], "name": exam[1], "class_name": exam[2],
                 "exam_date": exam[3], "subjects": exam[4] or [],
                 "max_marks": exam[5]}
    students = db.get_exam_students_for_tickets(exam_id)
    settings = db.get_settings()
    return render_template('hall_ticket/ticket_bulk.html',
                           exam=exam_dict, students=students, settings=settings)


# ─────────────────────────────────────────────────────────
# 5. STATS / SUMMARY API
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/stats/<int:exam_id>')
@login_required
def stats(exam_id):
    summary = db.get_exam_seating_summary(exam_id)
    students = db.get_exam_students_for_tickets(exam_id)
    seated = sum(r["student_count"] for r in summary)
    return {
        "total_rooms": len(summary),
        "seated": seated,
        "unseated": max(len(students) - seated, 0),
        "total_students": len(students),
        "rooms": summary
    }
