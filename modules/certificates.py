from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    create_certificate, get_certificates, get_certificate,
    delete_certificate, get_student, get_students,
    CERT_TYPES, CERT_TEMPLATES, _build_default_body,
    _academic_year_for_cert
)

certificates_bp = Blueprint("certificates", __name__, url_prefix="/certificates")

@certificates_bp.route("/")
@login_required
def index():
    cert_type = request.args.get("type", "").strip()
    search = request.args.get("q", "").strip()
    certs = get_certificates(cert_type or None, search or None)
    return render_template(
        "certificates/index.html",
        certs=certs, cert_types=CERT_TYPES,
        selected_type=cert_type, search=search
    )

@certificates_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    preselect = request.args.get("student_id", type=int)

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        cert_type = request.form.get("cert_type", "").strip()
        body = request.form.get("body", "").strip()
        remarks = request.form.get("remarks", "").strip()
        issue_date = request.form.get("issue_date") or None

        if not student_id or not cert_type:
            flash("Student aur certificate type zaroori hain", "error")
            return redirect(url_for("certificates.new"))

        try:
            res = create_certificate(
                student_id, cert_type, body, remarks,
                session["admin_id"], issue_date
            )
            flash(f"Certificate generate — {res['cert_no']}", "success")
            return redirect(url_for("certificates.view", cid=res["id"]))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("certificates.new"))

    # GET — show form. Agar student preselect hai, uska default body dikhao.
    students = []
    for s in get_students():
        students.append({
            "id": s[0], "name": s[1], "roll": s[2],
            "class_name": s[3], "section": s[4]
        })

    preselect_student = None
    default_body = ""
    if preselect:
        row = get_student(preselect)
        if row:
            keys = ["id","name","roll_no","class_name","section","gender","dob",
                    "parent_name","parent_phone","address","admission_date","status","created_at"]
            preselect_student = dict(zip(keys, row))

    # Naya certificate banate waqt pehla type default
    default_type = CERT_TYPES[0]
    if preselect_student:
        default_body = _build_default_body(default_type, preselect_student)

    return render_template(
        "certificates/form.html",
        students=students,
        cert_types=CERT_TYPES,
        templates=CERT_TEMPLATES,
        preselect_student=preselect_student,
        default_body=default_body,
        default_type=default_type,
        ay=_academic_year_for_cert()
    )

@certificates_bp.route("/<int:cid>")
@login_required
def view(cid):
    c = get_certificate(cid)
    if not c:
        abort(404)
    return render_template("certificates/print.html", c=c,
                           ay=_academic_year_for_cert())

@certificates_bp.route("/<int:cid>/delete", methods=["POST"])
@login_required
def remove(cid):
    delete_certificate(cid)
    flash("Certificate delete ho gaya", "success")
    return redirect(url_for("certificates.index"))
