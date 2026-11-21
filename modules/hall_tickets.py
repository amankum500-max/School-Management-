"""
Hall Ticket Module — Complete Routes
Place in modules/ or project root. Register in app.py: from modules.hall_tickets import hall_ticket_bp
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
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper


def _get_school_settings():
    try:
        raw = db.get_settings()
    except Exception:
        raw = {}

    if isinstance(raw, dict):
        name = raw.get("school_name") or raw.get("name") or "MY SCHOOL ACADEMY"
        return {
            **raw,
            "name": name,
            "school_name": name,
            "principal_signature_url": raw.get("principal_signature_url") or "",
        }

    if isinstance(raw, (list, tuple)) and len(raw) > 0:
        name = raw[1] if len(raw) > 1 and raw[1] else (raw[0] or "MY SCHOOL ACADEMY")
        return {
            "name": name,
            "school_name": name,
            "principal_signature_url": "",
        }

    return {
        "name": "MY SCHOOL ACADEMY",
        "school_name": "MY SCHOOL ACADEMY",
        "principal_signature_url": "",
    }


def _normalize_students(raw_students, default_class=""):
    formatted = []
    if not raw_students:
        return formatted

    for s in raw_students:
        if isinstance(s, dict):
            sid = s.get("id") or s.get("student_id") or ""
            name = s.get("name") or s.get("student_name") or ""
            roll = s.get("roll_no") or s.get("roll") or ""
            cls = s.get("class_name") or s.get("class") or default_class or ""
            sec = s.get("section") or ""
            father = s.get("father_name") or s.get("parent_name") or ""
            dob = s.get("dob") or ""
            gender = s.get("gender") or ""
            room = s.get("room_no") or ""
            seat = s.get("seat_no") or ""
            photo = s.get("photo_url") or s.get("photo") or ""
            sig = s.get("signature_url") or ""
        elif isinstance(s, (list, tuple)):
            sid = s[0] if len(s) > 0 else ""
            name = s[1] if len(s) > 1 else ""
            roll = s[2] if len(s) > 2 else ""
            cls = s[3] if len(s) > 3 and s[3] else (default_class or "")
            sec = s[4] if len(s) > 4 else ""
            father = s[7] if len(s) > 7 else ""
            dob = s[5] if len(s) > 5 else ""
            gender = s[6] if len(s) > 6 else ""
            room = ""
            seat = ""
            photo = s[13] if len(s) > 13 else ""
            sig = ""
        else:
            continue

        formatted.append({
            "id": sid,
            "name": name,
            "roll_no": roll,
            "class_name": cls,
            "section": sec,
            "father_name": father,
            "dob": dob,
            "gender": gender,
            "room_no": room,
            "seat_no": seat,
            "photo_url": photo,
            "signature_url": sig,
        })

    return formatted


def _fallback_students_for_class(exam_class):
    if not hasattr(db, "get_students"):
        return []
    try:
        all_students = db.get_students() or []
    except Exception:
        return []

    target_cls = str(exam_class or "").strip().lower()
    if not target_cls:
        return _normalize_students(all_students, default_class=exam_class or "")

    matched = []
    for s in all_students:
        s_cls = (s.get("class_name") or s.get("class") or "") if isinstance(s, dict) else (s[3] if len(s) > 3 else "")
        if str(s_cls).strip().lower() == target_cls:
            matched.append(s)

    return _normalize_students(matched, default_class=exam_class or "")


# ─────────────────────────────────────────────────────────
# 1. LIST EXAMS (select exam to generate hall tickets)
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/')
@login_required
def index():
    class_name = request.args.get('class_name', '')
    exams = db.get_exams(class_name=class_name or None)
    classes = db.get_classes_list()
    school_cfg = _get_school_settings()

    exam_list = []
    for e in exams:
        subjects_val = e[4] if len(e) > 4 and e[4] else []
        first_subject = subjects_val[0] if isinstance(subjects_val, (list, tuple)) and len(subjects_val) > 0 else ""
        exam_dict = {
            "id": e[0],
            "name": e[1],
            "class_name": e[2],
            "exam_date": e[3],
            "subjects": subjects_val,
            "subject": first_subject if isinstance(first_subject, str) else (first_subject.get("name") if isinstance(first_subject, dict) else ""),
            "max_marks": e[5] if len(e) > 5 else None,
            "seated_count": 0,
            "total_students": 0,
            "students": [],
        }
        try:
            summary = db.get_exam_seating_summary(e[0])
            exam_dict["seated_count"] = sum(r.get("student_count", r.get("count", 0)) for r in summary)

            raw_students = db.get_exam_students_for_tickets(e[0])
            students = _normalize_students(raw_students, default_class=e[2] or "")
            if not students:
                students = _fallback_students_for_class(e[2] or "")

            exam_dict["students"] = students
            exam_dict["total_students"] = len(students)
        except Exception:
            pass

        exam_list.append(exam_dict)

    return render_template(
        'hall_tickets/index.html',
        exams=exam_list,
        classes=classes,
        selected_class=class_name,
        school=school_cfg,
        settings=school_cfg,
    )


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
            flash(
                "Seating auto-assigned successfully!" if ok else "Auto-assign failed",
                "success" if ok else "danger",
            )
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
    total_set = sum(r.get("student_count", r.get("count", 0)) for r in summary)

    exam_dict = {
        "id": exam[0],
        "name": exam[1],
        "class_name": exam[2],
        "exam_date": exam[3],
        "subjects": exam[4] if len(exam) > 4 and exam[4] else [],
        "max_marks": exam[5] if len(exam) > 5 else None,
    }

    return render_template(
        'hall_tickets/manage.html',
        exam=exam_dict,
        students=students,
        summary=summary,
        seating_summary=summary,
        total_set=total_set,
    )


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

    req_class = request.args.get('class_name', '').strip()
    req_section = request.args.get('section', '').strip()

    exam_dict = {
        "id": exam[0],
        "name": exam[1],
        "class_name": req_class or exam[2],
        "exam_date": exam[3],
        "subjects": exam[4] if len(exam) > 4 and exam[4] else [],
        "max_marks": exam[5] if len(exam) > 5 else None,
    }

    student = {
        "id": student_row[0],
        "name": student_row[1],
        "roll_no": student_row[2],
        "class_name": req_class or (student_row[3] if len(student_row) > 3 else ""),
        "section": req_section or (student_row[4] if len(student_row) > 4 else ""),
        "parent_name": student_row[7] if len(student_row) > 7 else "",
        "father_name": student_row[7] if len(student_row) > 7 else "",
        "parent_phone": student_row[8] if len(student_row) > 8 else "",
        "photo_url": student_row[13] if len(student_row) > 13 else "",
    }

    seating_info = {"room_no": "—", "seat_no": "—"}
    for s in _normalize_students(db.get_exam_students_for_tickets(exam_id), default_class=exam[2] or ""):
        if str(s.get("id")) == str(student_id):
            seating_info = {
                "room_no": s.get("room_no") or "—",
                "seat_no": s.get("seat_no") or "—",
            }
            if s.get("class_name") and not req_class:
                student["class_name"] = s["class_name"]
            if s.get("section") and not req_section:
                student["section"] = s["section"]
            break

    settings = _get_school_settings()

    return render_template(
        'hall_tickets/print.html',
        exam=exam_dict,
        student=student,
        seating=seating_info,
        settings=settings,
        school=settings,
    )


# ─────────────────────────────────────────────────────────
# 4. BULK PRINT (all students of an exam)
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/bulk/<int:exam_id>')
@login_required
def bulk_print(exam_id):
    exam = db.get_exam(exam_id)
    if not exam:
        abort(404)
    exam_dict = {
        "id": exam[0],
        "name": exam[1],
        "class_name": exam[2],
        "exam_date": exam[3],
        "subjects": exam[4] if len(exam) > 4 and exam[4] else [],
        "max_marks": exam[5] if len(exam) > 5 else None,
    }
    students = _normalize_students(db.get_exam_students_for_tickets(exam_id), default_class=exam[2] or "")
    settings = _get_school_settings()

    return render_template(
        'hall_tickets/bulk_generate.html',
        exam=exam_dict,
        students=students,
        settings=settings,
        school=settings,
    )


# ─────────────────────────────────────────────────────────
# 5. STATS / SUMMARY API
# ─────────────────────────────────────────────────────────
@hall_ticket_bp.route('/stats/<int:exam_id>')
@login_required
def stats(exam_id):
    summary = db.get_exam_seating_summary(exam_id)
    students = db.get_exam_students_for_tickets(exam_id)
    seated = sum(r.get("student_count", r.get("count", 0)) for r in summary)
    return {
        "total_rooms": len(summary),
        "seated": seated,
        "unseated": max(len(students) - seated, 0),
        "total_students": len(students),
        "rooms": summary,
    }
