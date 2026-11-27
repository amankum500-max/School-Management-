from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    get_enquiries, get_enquiry, update_enquiry_status, delete_enquiry
)

admissions_bp = Blueprint("admissions", __name__, url_prefix="/admissions")

@admissions_bp.route("/")
@login_required
def index():
    status = request.args.get("status", "").strip()
    rows = get_enquiries(status or None)
    new_count = sum(1 for r in rows if r["status"] == "new")
    return render_template(
        "admissions/index.html",
        enquiries=rows,
        selected_status=status,
        new_count=new_count
    )

@admissions_bp.route("/<int:enquiry_id>", methods=["GET", "POST"])
@login_required
def view(enquiry_id):
    e = get_enquiry(enquiry_id)
    if not e:
        abort(404)

    if request.method == "POST":
        status = request.form.get("status", "new")
        note = request.form.get("admin_note", "")
        update_enquiry_status(enquiry_id, status, note)
        flash("Enquiry update ho gayi", "success")
        return redirect(url_for("admissions.view", enquiry_id=enquiry_id))

    return render_template("admissions/view.html", e=e)

@admissions_bp.route("/<int:enquiry_id>/delete", methods=["POST"])
@login_required
def remove(enquiry_id):
    delete_enquiry(enquiry_id)
    flash("Enquiry delete ho gayi", "success")
    return redirect(url_for("admissions.index"))
    import cloudinary.uploader
from database import (
    create_admission_application,
    get_admission_applications,
    get_admission_application,
    approve_admission_application,
    reject_admission_application,
    get_classes_list,
)

@admissions_bp.route("/apply", methods=["GET", "POST"])
def online_apply():
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        class_applied = request.form.get("class_applied", "").strip()
        parent_name = request.form.get("parent_name", "").strip()
        parent_phone = request.form.get("parent_phone", "").strip()

        if not all([student_name, class_applied, parent_name, parent_phone]):
            flash("Student naam, class, parent naam aur phone number zaroori hain.", "error")
            return render_template("admissions/apply.html", classes=get_classes_list())

        photo_url = None
        pic = request.files.get("profile_pic")
        if pic and pic.filename:
            try:
                up = cloudinary.uploader.upload(pic)
                photo_url = up.get("secure_url")
            except Exception as e:
                print(f"Admission photo upload error: {e}")
                flash("Photo upload nahi ho payi, lekin form submit ho raha hai.", "warning")

        app_data = {
            "student_name": student_name,
            "dob": request.form.get("dob") or None,
            "gender": request.form.get("gender") or None,
            "class_applied": class_applied,
            "section": request.form.get("section") or None,
            "parent_name": parent_name,
            "parent_phone": parent_phone,
            "address": request.form.get("address") or None,
            "photo_url": photo_url,
        }
        created = create_admission_application(app_data)
        return render_template("admissions/apply_success.html", application=created)

    return render_template("admissions/apply.html", classes=get_classes_list())

@admissions_bp.route("/applications")
@login_required
def applications():
    status = request.args.get("status", "pending").strip()
    rows = get_admission_applications(status=status)
    return render_template(
        "admissions/applications.html",
        applications=rows,
        selected_status=status,
    )

@admissions_bp.route("/applications/<int:app_id>/approve", methods=["POST"])
@login_required
def approve_application(app_id):
    app = get_admission_application(app_id)
    if not app:
        abort(404)

    result = approve_admission_application(
        app_id=app_id,
        class_name=request.form.get("class_name"),
        section=request.form.get("section"),
        roll_no=request.form.get("roll_no"),
        admin_note=request.form.get("admin_note", "").strip(),
    )
    if not result:
        flash("Application approve nahi ho saki (shayad pehle hi process ho chuki hai).", "error")
    else:
        flash(f"Admission approved! Student ID: {result['student_id']}, Roll No: {result['roll_no']}", "success")
    return redirect(url_for("admissions.applications", status="pending"))

@admissions_bp.route("/applications/<int:app_id>/reject", methods=["POST"])
@login_required
def reject_application(app_id):
    app = get_admission_application(app_id)
    if not app:
        abort(404)

    reject_admission_application(app_id, request.form.get("admin_note", "").strip())
    flash("Application reject kar di gayi.", "success")
    return redirect(url_for("admissions.applications", status="pending"))
    
