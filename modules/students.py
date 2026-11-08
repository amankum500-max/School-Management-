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
        # नया कोड: Cloudinary फोटो अपलोड लॉजिक यहाँ जोड़ें
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

        # डेटा डिक्शनरी में इमेज का URL जोड़ दें
        data['image_file'] = image_url 
        # ====================================================

        sid = create_student(data)
        flash(f"Student add ho gaya (ID: {sid})", "success")
        return redirect(url_for("students.list_students"))
        
    return render_template("students/form.html", student=None, mode="add", classes=get_classes_list())

# ... (baaki ka code same rahega)
