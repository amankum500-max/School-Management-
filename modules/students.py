from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    create_student, get_students, get_student,
    update_student, delete_student, get_classes_list
)

students_bp = Blueprint("students", __name__, url_prefix="/students")

@students_bp.route("/")
@login_required
def list_students():
    search = request.args.get("q", "").strip()
    class_name = request.args.get("class", "").strip()
    rows = get_students(search or None, class_name or None)
    students = [
        {"id": r[0], "name": r[1], "roll_no": r[2],
         "class_name": r[3], "section": r[4],
         "parent_phone": r[5], "status": r[6]}
        for r in rows
    ]
    @students_bp.route("/")
@login_required
def list_students():
    search = request.args.get("q", "").strip()
    class_name = request.args.get("class", "").strip()
    status = request.args.get("status", "active")
    rows = get_students(search or None, class_name or None, status)
    ...
    return render_template(
        "students/list.html",
        students=students,
        search=search,
        selected_class=class_name,
        classes=get_classes_list()
    )

@students_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("name"):
            flash("Name zaroori hai", "error")
            return redirect(url_for("students.add_student"))
        sid = create_student(data)
        flash(f"Student add ho gaya (ID: {sid})", "success")
        return redirect(url_for("students.list_students"))
    return render_template("students/form.html", student=None, mode="add")

@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))
    return render_template("students/profile.html", student=student)

@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))

    if request.method == "POST":
        data = request.form.to_dict()
        update_student(student_id, data)
        flash("Student update ho gaya", "success")
        return redirect(url_for("students.view_student", student_id=student_id))

    return render_template("students/form.html", student=student, mode="edit")

@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def remove_student(student_id):
    delete_student(student_id)
    flash("Student delete ho gaya", "success")
    return redirect(url_for("students.list_students"))
    from database import get_student_transport

@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))
    transport = get_student_transport(student_id)    # ← NEW
    return render_template("students/profile.html",
                           student=student, transport=transport)
    from database import get_student_library_history    # import section mein

@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = [...]
    student = dict(zip(keys, row))
    transport = get_student_transport(student_id)
    library_hist = get_student_library_history(student_id)    # ← NEW
    return render_template("students/profile.html",
                           student=student, transport=transport,
                           library_hist=library_hist)
    from database import get_medical_record       # import section mein

@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = [...]
    student = dict(zip(keys, row))
    transport = get_student_transport(student_id)
    library_hist = get_student_library_history(student_id)
    medical = get_medical_record(student_id)      # ← NEW
    return render_template("students/profile.html",
                           student=student, transport=transport,
                           library_hist=library_hist, medical=medical)
