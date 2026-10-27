from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, abort
)
from modules.auth import login_required, role_required
from database import (
    get_student, get_students, get_students_without_photos,
    update_student_photo_url, count_students_with_photos,
    get_classes_list
)
import photo_service

photos_bp = Blueprint("photos", __name__, url_prefix="/photos")


@photos_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    stats = count_students_with_photos()
    without = get_students_without_photos(limit=20) if False else \
              get_students_without_photos()[:30]
    configured = photo_service.is_configured()

    return render_template("photos/index.html",
                           stats=stats, without=without,
                           configured=configured,
                           classes=get_classes_list())


@photos_bp.route("/upload/<int:student_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def upload(student_id):
    student_row = get_student(student_id)
    if not student_row:
        return jsonify({"ok": False, "error": "Student not found"}), 404

    file = request.files.get("photo")
    if not file:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    result = photo_service.upload_student_photo(student_id, file)

    if result["ok"]:
        update_student_photo_url(student_id, result["url"])
        return jsonify({"ok": True, "url": result["url"]})

    return jsonify({"ok": False, "error": result.get("error", "Upload failed")}), 400


@photos_bp.route("/delete/<int:student_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete(student_id):
    photo_service.delete_student_photo(student_id)
    update_student_photo_url(student_id, None)
    flash("Photo delete ho gayi", "success")
    return redirect(url_for("students.view_student", student_id=student_id))


# ---------- Bulk upload ----------
@photos_bp.route("/bulk", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def bulk():
    class_name = request.args.get("class", "").strip()

    if request.method == "POST":
        # Match uploaded filenames to student IDs or roll numbers
        # Format: <roll_no>.<ext> OR <student_id>.<ext>
        files = request.files.getlist("photos")
        matched = 0
        failed = 0
        details = []

        if not files or all(not f.filename for f in files):
            flash("Koi photo select nahi ki", "error")
            return redirect(url_for("photos.bulk"))

        # Build lookup maps
        all_students = {}
        for s in get_students():
            # s = (id, name, roll_no, class_name, section, phone, status)
            if s[2]:  # roll_no
                all_students[str(s[2]).strip().lower()] = s[0]
            all_students[str(s[0])] = s[0]  # student_id
            # Also try "roll_class" combined (safer when rolls repeat)
            if s[2] and s[3]:
                key = f"{s[2]}_{s[3]}".lower().replace(" ", "")
                all_students[key] = s[0]
            if s[2] and s[3] and s[4]:
                key = f"{s[2]}_{s[3]}_{s[4]}".lower().replace(" ", "")
                all_students[key] = s[0]

        for file in files:
            if not file or not file.filename:
                continue

            # Extract roll/id from filename
            import os as _os
            base = _os.path.splitext(file.filename)[0].strip().lower()

            student_id = all_students.get(base)
            if not student_id:
                failed += 1
                details.append({"file": file.filename,
                                "status": "no_match"})
                continue

            result = photo_service.upload_student_photo(student_id, file)
            if result["ok"]:
                update_student_photo_url(student_id, result["url"])
                matched += 1
                details.append({"file": file.filename,
                                "status": "ok",
                                "student_id": student_id})
            else:
                failed += 1
                details.append({"file": file.filename,
                                "status": "upload_error",
                                "error": result.get("error", "")})

        flash(f"{matched} photos uploaded, {failed} failed", 
              "success" if failed == 0 else "warning")
        return render_template("photos/bulk_result.html",
                               matched=matched, failed=failed,
                               details=details)

    students_without = get_students_without_photos(class_name or None)

    return render_template("photos/bulk.html",
                           students=students_without,
                           classes=get_classes_list(),
                           selected_class=class_name)
    from database import (
    ..., add_student_document, get_student_documents,
    delete_student_document, DOC_TYPES
)

@photos_bp.route("/documents/<int:student_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def upload_document(student_id):
    file = request.files.get("document")
    doc_type = request.form.get("doc_type", "other")
    doc_name = request.form.get("doc_name", "").strip() or "Untitled"

    if not file:
        flash("File select karo", "error")
        return redirect(url_for("students.view_student", student_id=student_id))

    result = photo_service.upload_student_document(student_id, doc_type, file, doc_name)

    if result["ok"]:
        add_student_document(student_id, doc_type, doc_name, result["url"],
                             result["size"], result["type"], session["admin_id"])
        flash(f"'{doc_name}' upload ho gaya", "success")
    else:
        flash(f"Upload fail: {result.get('error')}", "error")

    return redirect(url_for("students.view_student", student_id=student_id))


@photos_bp.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete_document(doc_id):
    student_id = request.form.get("student_id", type=int)
    url = delete_student_document(doc_id)
    if url:
        try:
            from database import get_conn
            # Optionally delete from storage too
            pass
        except Exception:
            pass
    flash("Document delete ho gaya", "success")
    return redirect(url_for("students.view_student", student_id=student_id))
