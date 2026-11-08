from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required, role_required

# Cloudinary Imports (फोटो अपलोड के लिए)
import cloudinary
import cloudinary.uploader

# Saare database functions ek jagah import kiye hain
from database import (
    create_student, get_students, get_student,
    update_student, delete_student, get_classes_list,
    get_student_transport, get_student_library_history,
    get_medical_record, get_student_hostel, get_student_discounts,
    check_duplicate_student
)

students_bp = Blueprint("students", __name__, url_prefix="/students")

@students_bp.route("/")
@login_required
def list_students():
    search = request.args.get("q", "").strip()
    class_name = request.args.get("class", "").strip()
    status = request.args.get("status", "active")
    
    rows = get_students(search or None, class_name or None, status)
    
    students = [
        {"id": r[0], "name": r[1], "roll_no": r[2],
         "class_name": r[3], "section": r[4],
         "parent_phone": r[5], "status": r[6]}
        for r in rows
    ]
    
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
            
        # Phase 51D: Duplicate Check
        dups = check_duplicate_student(
            data.get("name"),
            data.get("roll_no"),
            data.get("parent_phone")
        )
        force = request.form.get("_force_create") == "1"
        
        if dups and not force:
            return render_template("students/duplicate_warning.html",
                                   data=data, duplicates=dups,
                                   classes=get_classes_list())

        # ====================================================
        # Cloudinary फोटो अपलोड लॉजिक
        # ====================================================
        file_to_upload = request.files.get('profile_pic')
        image_url = None
        
        if file_to_upload and file_to_upload.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(file_to_upload)
                image_url = upload_result['secure_url']
            except Exception as e:
                print(f"Cloudinary Error: {e}")
                flash("Photo upload fail ho gaya, par baaki data save ho raha hai.", "warning")

        # Yahan image_file ki jagah photo_url kar diya hai
        data['photo_url'] = image_url 
        # ====================================================

        sid = create_student(data)
        flash(f"Student add ho gaya (ID: {sid})", "success")
        return redirect(url_for("students.list_students"))
        
    return render_template("students/form.html", student=None, mode="add", classes=get_classes_list())


# ====================================================
# YAHAN SE BAAKI CODE SHURU HOTA HAI
# ====================================================

@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
        
    # Yahan image_file ki jagah photo_url kar diya hai
    keys = ["id", "name", "roll_no", "class_name", "section", "gender", "dob",
            "parent_name", "parent_phone", "address", "admission_date", "status", 
            "created_at", "photo_url"]
    student = dict(zip(keys, row))

    transport = get_student_transport(student_id)
    library_hist = get_student_library_history(student_id)
    medical = get_medical_record(student_id)
    hostel_info = get_student_hostel(student_id)
    discounts = get_student_discounts(student_id, active_only=True)

    return render_template("students/profile.html",
                           student=student, 
                           transport=transport,
                           library_hist=library_hist, 
                           medical=medical,
                           hostel_info=hostel_info,
                           discounts=discounts)

@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
        
    # Yahan bhi image_file ki jagah photo_url kar diya hai
    keys = ["id", "name", "roll_no", "class_name", "section", "gender", "dob",
            "parent_name", "parent_phone", "address", "admission_date", "status", 
            "created_at", "photo_url"]
    student = dict(zip(keys, row))

    if request.method == "POST":
        data = request.form.to_dict()
        
        # Edit karte waqt nayi photo upload
        file_to_upload = request.files.get('profile_pic')
        if file_to_upload and file_to_upload.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(file_to_upload)
                data['photo_url'] = upload_result['secure_url'] # Yahan bhi photo_url kar diya
            except Exception as e:
                print(f"Cloudinary Error: {e}")
                flash("Photo upload fail ho gaya.", "warning")
        
        update_student(student_id, data)
        flash("Student update ho gaya", "success")
        return redirect(url_for("students.view_student", student_id=student_id))

    return render_template("students/form.html", student=student, mode="edit", classes=get_classes_list())

@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def remove_student(student_id):
    delete_student(student_id)
    flash("Student delete ho gaya", "success")
    return redirect(url_for("students.list_students"))
