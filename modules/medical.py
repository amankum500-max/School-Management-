from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    get_medical_record, save_medical_record, delete_medical_record,
    get_vaccinations, add_vaccination, delete_vaccination,
    get_student, get_students, BLOOD_GROUPS,
    count_students_with_medical, get_students_missing_medical,
    get_students_with_allergies
)

medical_bp = Blueprint("medical", __name__, url_prefix="/medical")

@medical_bp.route("/")
@login_required
def index():
    stats = {
        "with_records": count_students_with_medical(),
        "missing": len(get_students_missing_medical(limit=500)),
        "allergies": len(get_students_with_allergies())
    }
    missing = get_students_missing_medical(limit=20)
    allergies = get_students_with_allergies()

    return render_template("medical/index.html",
                           stats=stats, missing=missing, allergies=allergies)

@medical_bp.route("/student/<int:student_id>", methods=["GET", "POST"])
@login_required
def record(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save":
            save_medical_record(student_id, request.form.to_dict(), session["admin_id"])
            flash("Medical record save ho gaya", "success")
            return redirect(url_for("medical.record", student_id=student_id))

        elif action == "add_vax":
            vname = request.form.get("vaccine_name", "").strip()
            vdate = request.form.get("date_given", "").strip()
            if not vname or not vdate:
                flash("Vaccine name aur date zaroori", "error")
            else:
                add_vaccination(
                    student_id, vname, vdate,
                    request.form.get("dose_no", ""),
                    request.form.get("vax_notes", "")
                )
                flash("Vaccination add ho gayi", "success")
            return redirect(url_for("medical.record", student_id=student_id))

        elif action == "delete":
            delete_medical_record(student_id)
            flash("Medical record delete ho gaya", "success")
            return redirect(url_for("medical.record", student_id=student_id))

    mr = get_medical_record(student_id)
    vaxes = get_vaccinations(student_id)

    return render_template("medical/record.html",
                           student=student, mr=mr, vaxes=vaxes,
                           blood_groups=BLOOD_GROUPS)

@medical_bp.route("/vax/<int:vid>/delete", methods=["POST"])
@login_required
def delete_vax(vid):
    student_id = request.form.get("student_id", type=int)
    delete_vaccination(vid)
    flash("Vaccination delete ho gayi", "success")
    return redirect(url_for("medical.record", student_id=student_id))
