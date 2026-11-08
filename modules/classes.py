from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response
import csv, io
from modules.auth import login_required, role_required
from database import (
    get_advanced_classes_list, create_new_class, archive_class, restore_class,
    get_class_by_id, update_class_details, get_students, promote_students, get_classes_stats,
    add_section_to_class, get_class_subjects, add_class_subject, delete_class_subject,
    transfer_student, get_class_students_for_export, auto_assign_subjects,
    get_next_roll_number  # <--- Yahan add kar diya hai
)

classes_bp = Blueprint("classes", __name__, url_prefix="/classes")

@classes_bp.route("/", methods=["GET"])
@login_required
def index():
    search = request.args.get("q", "").strip()
    tab = request.args.get("tab", "active")
    stats = get_classes_stats()
    classes = get_advanced_classes_list(search or None, is_active=(tab == "active"))
    return render_template("classes/list.html", classes=classes, stats=stats, search=search, tab=tab)

@classes_bp.route("/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_class():
    class_name, section = request.form.get("class_name", "").strip(), request.form.get("section", "A").strip().upper()
    capacity, class_teacher = request.form.get("capacity", 40, type=int), request.form.get("class_teacher", "").strip()
    subjects, academic_year = request.form.get("subjects", "").strip(), request.form.get("academic_year", "2024-25").strip()
    if not class_name: flash("Class ka naam zaroori hai!", "error")
    else:
        result = create_new_class(class_name, section, capacity, class_teacher, subjects, academic_year)
        if result:
            auto_assign_subjects(result) # <--- AUTOMATION
            flash(f"Class {class_name}-{section} aur default subjects add ho gaye!", "success")
        else: flash("Error ya class pehle se hai.", "error")
    return redirect(url_for("classes.index"))

@classes_bp.route("/add_section/<int:class_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_section(class_id):
    new_section = request.form.get("new_section", "").strip().upper()
    if add_section_to_class(class_id, new_section, request.form.get("capacity", 40, type=int), request.form.get("class_teacher", "").strip()):
        flash(f"Section {new_section} add ho gaya!", "success")
    else: flash("Section add fail ho gaya.", "error")
    return redirect(url_for("classes.index"))

@classes_bp.route("/edit/<int:class_id>", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def edit_class(class_id):
    cls = get_class_by_id(class_id)
    if not cls: abort(404)
    if request.method == "POST":
        update_class_details(class_id, request.form.get("class_name"), request.form.get("section"), request.form.get("capacity", 40, type=int), request.form.get("class_teacher"), request.form.get("subjects"), request.form.get("academic_year"))
        flash("Class updated!", "success"); return redirect(url_for("classes.index"))
    return render_template("classes/edit.html", cls=cls)

@classes_bp.route("/archive/<int:class_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def archive(class_id): archive_class(class_id); return redirect(url_for("classes.index"))

@classes_bp.route("/restore/<int:class_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def restore(class_id): restore_class(class_id); return redirect(url_for("classes.index", tab="archived"))

@classes_bp.route("/<int:class_id>")
@login_required
def detail(class_id):
    cls = get_class_by_id(class_id)
    if not cls: abort(404)
    rows = get_students(class_name=cls['class_name'], status="active")
    students = [{"id": r[0], "name": r[1], "roll_no": r[2], "parent_phone": r[5]} for r in rows if r[4] == cls['section']]
    return render_template("classes/detail.html", cls=cls, students=students, subjects=get_class_subjects(class_id))

@classes_bp.route("/promote/<int:class_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def promote(class_id):
    cls = get_class_by_id(class_id)
    promote_students(cls['class_name'], cls['section'], request.form.get("new_class"), request.form.get("new_section").upper())
    flash("Promotion successful!", "success"); return redirect(url_for("classes.index"))

@classes_bp.route("/<int:class_id>/add_subject", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_subject(class_id):
    add_class_subject(class_id, request.form.get("subject_name"), request.form.get("teacher_name"))
    return redirect(url_for("classes.detail", class_id=class_id))

@classes_bp.route("/delete_subject/<int:subject_id>/<int:class_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete_subject(subject_id, class_id):
    delete_class_subject(subject_id); return redirect(url_for("classes.detail", class_id=class_id))

@classes_bp.route("/transfer_student/<int:student_id>/<int:class_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def transfer(student_id, class_id):
    transfer_student(student_id, request.form.get("new_class"), request.form.get("new_section").upper())
    return redirect(url_for("classes.detail", class_id=class_id))

@classes_bp.route("/export/<int:class_id>")
@login_required
def export_csv(class_id):
    cls = get_class_by_id(class_id); students = get_class_students_for_export(cls['class_name'], cls['section'])
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(['Roll No', 'Name', 'Gender', 'Parent', 'Phone'])
    for s in students: writer.writerow(s)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=Class_{cls['class_name']}_{cls['section']}.csv"})
@students_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        data = request.form.to_dict()
        
        if not data.get("name"):
            flash("Name zaroori hai", "error")
            return redirect(url_for("students.add_student"))
            
        # YAHAN SE ADD KAREIN
        if not data.get("roll_no") or data.get("roll_no").strip() == "":
            data["roll_no"] = str(get_next_roll_number(data.get("class_name"), data.get("section")))
        # YAHAN TAK

        # Phase 51D: Duplicate Check
        dups = check_duplicate_student(
            data.get("name"),
            data.get("roll_no"),
            data.get("parent_phone")
        )
        # ... (baaki code)
