from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    create_exam, get_exams, get_exam, delete_exam,
    get_marks_grid, save_mark, get_student_marks_report,
    get_merit_list, get_exam_stats, get_student,
    get_classes_list
)

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")

@exams_bp.route("/")
@login_required
def index():
    selected = request.args.get("class", "").strip()
    rows = get_exams(selected or None)
    return render_template(
        "exams/index.html",
        exams=[
            {"id": r[0], "name": r[1], "class_name": r[2],
             "exam_date": r[3], "subjects": r[4] or [], "max_marks": r[5]}
            for r in rows
        ],
        classes=get_classes_list(),
        selected_class=selected
    )

@exams_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        name = request.form["name"].strip()
        class_name = request.form["class_name"].strip()
        exam_date = request.form.get("exam_date") or None
        subjects_raw = request.form.get("subjects", "")
        subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]
        max_marks = int(request.form.get("max_marks") or 100)

        if not subjects:
            flash("Kam se kam ek subject likho (comma separated)", "error")
            return redirect(url_for("exams.add"))

        eid = create_exam(name, class_name, exam_date, subjects, max_marks)
        flash(f"Exam create ho gaya (ID: {eid})", "success")
        return redirect(url_for("exams.marks_entry", exam_id=eid))

    return render_template("exams/form.html", classes=get_classes_list())

@exams_bp.route("/<int:exam_id>/marks", methods=["GET", "POST"])
@login_required
def marks_entry(exam_id):
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
        return redirect(url_for("exams.marks_entry", exam_id=exam_id))

    exam, students, marks = get_marks_grid(exam_id)
    if not exam:
        abort(404)
    return render_template(
        "exams/marks_entry.html",
        exam=exam, students=students, marks=marks
    )

@exams_bp.route("/<int:exam_id>/report/<int:student_id>")
@login_required
def report_card(exam_id, student_id):
    exam = get_exam(exam_id)
    row = get_student(student_id)
    if not exam or not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))
    exam_dict = {
        "id": exam[0], "name": exam[1], "class_name": exam[2],
        "exam_date": exam[3], "subjects": exam[4] or [], "max_marks": exam[5]
    }
    marks = get_student_marks_report(exam_id, student_id)
    total = sum(v for v in marks.values() if v is not None)
    max_total = exam_dict["max_marks"] * len(exam_dict["subjects"])
    percent = round((total / max_total) * 100, 1) if max_total else 0

    if percent >= 90: grade = "A+"
    elif percent >= 80: grade = "A"
    elif percent >= 70: grade = "B"
    elif percent >= 60: grade = "C"
    elif percent >= 33: grade = "D"
    else: grade = "F"

    return render_template(
        "exams/report_card.html",
        exam=exam_dict, student=student, marks=marks,
        total=total, max_total=max_total, percent=percent, grade=grade
    )

@exams_bp.route("/<int:exam_id>/merit")
@login_required
def merit(exam_id):
    exam = get_exam(exam_id)
    if not exam:
        abort(404)
    exam_dict = {
        "id": exam[0], "name": exam[1], "class_name": exam[2],
        "exam_date": exam[3], "subjects": exam[4] or [], "max_marks": exam[5]
    }
    rows = get_merit_list(exam_id)
    students = [
        {"rank": i+1, "id": r[0], "name": r[1], "roll": r[2],
         "section": r[3], "total": r[4], "subjects_done": r[5]}
        for i, r in enumerate(rows)
    ]
    stats = get_exam_stats(exam_id)
    return render_template(
        "exams/merit.html", exam=exam_dict, students=students, stats=stats
    )

@exams_bp.route("/<int:exam_id>/delete", methods=["POST"])
@login_required
def remove(exam_id):
    delete_exam(exam_id)
    flash("Exam delete ho gaya", "success")
    return redirect(url_for("exams.index"))
