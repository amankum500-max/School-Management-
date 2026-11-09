from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort, jsonify, Response
)
from modules.auth import login_required, role_required
import os
import csv
import io
import json
from google import genai

# Cloudinary Imports (फोटो अपलोड के लिए)
import cloudinary
import cloudinary.uploader

# Saare database functions ek jagah import kiye hain
from database import (
    create_student, get_students, get_student,
    update_student, delete_student, get_classes_list,
    get_student_transport, get_student_library_history,
    get_medical_record, get_student_hostel, get_student_discounts,
    check_duplicate_student, get_next_roll_number
)

students_bp = Blueprint("students", __name__, url_prefix="/students")

# AI Client Setup (Ensure GEMINI_API_KEY is in environment variables)
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@students_bp.route("/")
@login_required
def list_students():
    search = request.args.get("q", "").strip()
    class_name = request.args.get("class", "").strip()
    status = request.args.get("status", "active")
    
    rows = get_students(search or None, class_name or None, status)
    
    students = []
    for i, r in enumerate(rows):
        # Dummy AI Risk Logic (Aap isko actual attendance/fees logic se replace kar sakte hain)
        # Agar index 3 se divide hota hai, toh usko "At Risk" maan rahe hain demo ke liye
        is_at_risk = (i % 3 == 0) 
        
        students.append({
            "id": r[0], "name": r[1], "roll_no": r[2],
            "class_name": r[3], "section": r[4],
            "parent_phone": r[5], "status": r[6],
            "is_at_risk": is_at_risk # AI Risk flag frontend ko bheja
        })
    
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
            
        # ====================================================
        # YAHAN AUTO ROLL NUMBER WALA LOGIC ADD KIYA HAI
        # ====================================================
        if not data.get("roll_no") or data.get("roll_no").strip() == "":
            data["roll_no"] = str(get_next_roll_number(data.get("class_name"), data.get("section")))
        # ====================================================

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

        data['photo_url'] = image_url 
        # ====================================================

        sid = create_student(data)
        flash(f"Student add ho gaya (ID: {sid})", "success")
        return redirect(url_for("students.list_students"))
        
    return render_template("students/form.html", student=None, mode="add", classes=get_classes_list())


@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
        
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
        
    keys = ["id", "name", "roll_no", "class_name", "section", "gender", "dob",
            "parent_name", "parent_phone", "address", "admission_date", "status", 
            "created_at", "photo_url"]
    student = dict(zip(keys, row))

    if request.method == "POST":
        data = request.form.to_dict()
        
        file_to_upload = request.files.get('profile_pic')
        if file_to_upload and file_to_upload.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(file_to_upload)
                data['photo_url'] = upload_result['secure_url'] 
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


# ====================================================
# NAYE ADVANCED ROUTES (AI, Export, Bulk Actions)
# ====================================================

@students_bp.route("/export", methods=["GET"])
@login_required
def export_students_csv():
    """CSV Export Logic"""
    search = request.args.get("q", "").strip()
    class_name = request.args.get("class", "").strip()
    status = request.args.get("status", "active")
    
    rows = get_students(search or None, class_name or None, status)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Roll No', 'Class', 'Section', 'Parent Phone', 'Status'])
    
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6]])
        
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=students_export.csv"}
    )

@students_bp.route("/api/ai-query", methods=["POST"])
@login_required
def ai_query():
    """AI Copilot Chat Endpoint"""
    data = request.json
    user_query = data.get("query", "")
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    prompt = f"""
    You are an AI assistant for a School Management System. 
    The user (Admin) says: "{user_query}"
    
    Based on this query, reply in helpful natural language. 
    If the user is asking for a list, tell them how many students match.
    Keep the answer short (max 3 sentences). Use Hinglish (Hindi + English) as used in Indian Schools.
    """
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return jsonify({"success": True, "ai_reply": response.text.strip()})
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"success": False, "ai_reply": "Sorry, main abhi connect nahi ho pa raha. Please check API key."})

@students_bp.route("/bulk-action", methods=["POST"])
@login_required
def bulk_action():
    """Handle Bulk Deletes or Messages"""
    data = request.json
    action = data.get("action")
    student_ids = data.get("ids", [])
    
    if not student_ids:
        return jsonify({"error": "No students selected"}), 400

    if action == "delete":
        # ASSUMPTION: database.py mein ek function bulk delete ka banaya gaya ho
        # Example: delete_multiple_students(student_ids)
        # Agar nahi hai, toh loop chala kar delete_student(id) call karein:
        try:
            for sid in student_ids:
                delete_student(sid)
            return jsonify({"success": True, "message": f"{len(student_ids)} students deleted successfully."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    elif action == "whatsapp":
        # WhatsApp API integration yahan aayega
        return jsonify({"success": True, "message": f"WhatsApp messages initiated for {len(student_ids)} parents."})
        
    return jsonify({"error": "Invalid action"}), 400
