from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from database import (
    verify_teacher, get_teacher_classes, get_teacher_today_schedule,
    get_teacher_homework, get_attendance_for_date, mark_attendance,
    bulk_mark_attendance, class_attendance_today,
    create_homework, get_exams, get_marks_grid, save_mark,
    get_students, get_student
)

teacher_portal_bp = Blueprint("teacher_portal", __name__, url_prefix="/teacher")

def teacher_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "teacher_id" not in session:
            return redirect(url_for("teacher_portal.login"))
        return f(*args, **kwargs)
    return wrapper

# ---------- Auth ----------
@teacher_portal_bp.route("/login", methods=["GET", "POST"])
def login():
    if "teacher_id" in session:
        return redirect(url_for("teacher_portal.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        t = verify_teacher(username, password)
        if t:
            session["teacher_id"] = t["id"]
            session["teacher_staff_id"] = t["staff_id"]
            session["teacher_name"] = t["name"]
            session["teacher_username"] = t["username"]
            return redirect(url_for("teacher_portal.dashboard"))
        flash("Galat username ya password", "error")
    return render_template("teacher_portal/login.html")

@teacher_portal_bp.route("/logout")
def logout():
    for k in ["teacher_id", "teacher_staff_id", "teacher_name", "teacher_username"]:
        session.pop(k, None)
    return redirect(url_for("teacher_portal.login"))

# ---------- Dashboard ----------
@teacher_portal_bp.route("/")
@teacher_required
def dashboard():
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)
    schedule = get_teacher_today_schedule(staff_id)
    homework = get_teacher_homework(staff_id, limit=5)
    today = date.today()
    weekday_name = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][today.weekday()]

    return render_template(
        "teacher_portal/dashboard.html",
        classes=classes, schedule=schedule, homework=homework,
        today=today, weekday_name=weekday_name
    )

# ---------- Attendance ----------
@teacher_portal_bp.route("/attendance")
@teacher_required
def attendance():
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)

    if not classes:
        return render_template("teacher_portal/attendance.html",
                               classes=[], students=[], selected=None, date=None)

    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()
    date_str = request.args.get("date") or date.today().isoformat()

    # Verify teacher has this class
    allowed = any(c["class_name"] == class_name and (c["section"] or '') == section
                  for c in classes)
    if not allowed and class_name:
        flash("Aap is class ke teacher nahi hain", "error")
        return redirect(url_for("teacher_portal.attendance"))

    students = []
    summary = None
    if class_name:
        raw = get_attendance_for_date(class_name, section, date_str)
        students = [
            {"id": r[0], "name": r[1], "roll": r[2],
             "class_name": r[3], "section": r[4], "status": r[5]}
            for r in raw
        ]
        summary = class_attendance_today(class_name, section, date_str)

    return render_template(
        "teacher_portal/attendance.html",
        classes=classes, students=students,
        selected={"class_name": class_name, "section": section} if class_name else None,
        date=date_str, summary=summary
    )

@teacher_portal_bp.route("/attendance/mark", methods=["POST"])
@teacher_required
def attendance_mark():
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)
    class_name = request.form["class"]
    section = request.form.get("section", "")
    allowed = any(c["class_name"] == class_name and (c["section"] or '') == section
                  for c in classes)
    if not allowed:
        flash("Unauthorized", "error")
        return redirect(url_for("teacher_portal.attendance"))

    student_id = int(request.form["student_id"])
    date_str = request.form["date"]
    status = request.form["status"]
    mark_attendance(student_id, date_str, status, session["teacher_id"])
    return redirect(url_for(
        "teacher_portal.attendance",
        **{"class": class_name, "section": section, "date": date_str}
    ))

@teacher_portal_bp.route("/attendance/mark-all", methods=["POST"])
@teacher_required
def attendance_mark_all():
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)
    class_name = request.form["class"]
    section = request.form.get("section", "")
    allowed = any(c["class_name"] == class_name and (c["section"] or '') == section
                  for c in classes)
    if not allowed:
        flash("Unauthorized", "error")
        return redirect(url_for("teacher_portal.attendance"))

    date_str = request.form["date"]
    status = request.form["status"]
    bulk_mark_attendance(class_name, section, date_str, status, session["teacher_id"])
    flash(f"Poori class ko '{status}' mark kar diya", "success")
    return redirect(url_for(
        "teacher_portal.attendance",
        **{"class": class_name, "section": section, "date": date_str}
    ))

# ---------- Homework ----------
@teacher_portal_bp.route("/homework")
@teacher_required
def homework_list():
    staff_id = session["teacher_staff_id"]
    items = get_teacher_homework(staff_id, limit=100)
    today = date.today()
    for h in items:
        if h["due_date"]:
            h["status"] = "overdue" if h["due_date"] < today else (
                "today" if h["due_date"] == today else "upcoming")
        else:
            h["status"] = "no_due"
    return render_template("teacher_portal/homework_list.html", items=items)

@teacher_portal_bp.route("/homework/add", methods=["GET", "POST"])
@teacher_required
def homework_add():
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)

    if not classes:
        flash("Aapko koi class assign nahi hai", "error")
        return redirect(url_for("teacher_portal.dashboard"))

    if request.method == "POST":
        data = request.form.to_dict()
        # Verify class
        allowed = any(c["class_name"] == data.get("class_name")
                     and (c["section"] or '') == (data.get("section") or '')
                     for c in classes)
        if not allowed:
            flash("Unauthorized class", "error")
            return redirect(url_for("teacher_portal.homework_add"))

        # Admin ID required for created_by — use staff_id mapping. If no admin,
        # we can fallback to first admin or store teacher id. For simplicity use
        # session teacher_id as created_by (admin_id field allows NULL if we adjust)
        # But schema requires admins reference. Simplest: fetch admin id 1 (default).
        from supabase_client import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM admins LIMIT 1;")
        row = cur.fetchone()
        admin_id = row[0] if row else None
        cur.close()
        conn.close()

        create_homework(data, admin_id)
        flash("Homework post ho gaya", "success")
        return redirect(url_for("teacher_portal.homework_list"))

    return render_template(
        "teacher_portal/homework_form.html",
        classes=classes,
        today=date.today().isoformat()
    )

# ---------- Marks ----------
@teacher_portal_bp.route("/marks")
@teacher_required
def marks_list():
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)
    class_names = list(set(c["class_name"] for c in classes))
    exams = []
    for cn in class_names:
        exams.extend(get_exams(cn))
    return render_template("teacher_portal/marks_list.html",
                           exams=exams, classes=classes)

@teacher_portal_bp.route("/marks/<int:exam_id>", methods=["GET", "POST"])
@teacher_required
def marks_entry(exam_id):
    staff_id = session["teacher_staff_id"]
    classes = get_teacher_classes(staff_id)
    allowed_class_names = set(c["class_name"] for c in classes)

    exam, students, marks = get_marks_grid(exam_id)
    if not exam:
        abort(404)
    if exam["class_name"] not in allowed_class_names:
        flash("Aap is exam ke teacher nahi hain", "error")
        return redirect(url_for("teacher_portal.marks_list"))

    if request.method == "POST":
        for key, val in request.form.items():
            if key.startswith("mark_"):
                _, sid, subj = key.split("_", 2)
                if val.strip() == "":
                    continue
                try:
                    save_mark(exam_id, int(sid), subj, int(float(val)))
                except ValueError:
                    pass
        flash("Marks save ho gaye", "success")
        return redirect(url_for("teacher_portal.marks_entry", exam_id=exam_id))

    return render_template("teacher_portal/marks_entry.html",
                           exam=exam, students=students, marks=marks)
