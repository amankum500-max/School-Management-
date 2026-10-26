import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify
)
from modules.auth import login_required, role_required
from database import (
    get_students, get_student, get_sms_logs, get_sms_stats,
    get_sms_templates, get_sms_template, log_sms,
    update_sms_template_id, was_sms_sent_recently,
    get_students_for_reminder, get_settings
)
import sms_service

sms_bp = Blueprint("sms", __name__, url_prefix="/sms")

@sms_bp.route("/")
@login_required
@role_required("super_admin", "admin", "accountant")
def index():
    stats = get_sms_stats()
    logs = get_sms_logs(limit=30)
    configured = sms_service.is_configured()
    provider = os.getenv("SMS_PROVIDER", "msg91")
    return render_template("sms/index.html",
                           stats=stats, logs=logs,
                           configured=configured, provider=provider)

# ---------- Compose & Send ----------
@sms_bp.route("/send", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin", "accountant")
def send():
    templates = get_sms_templates()
    mode = request.args.get("mode", "custom")   # custom | defaulters | absent

    if request.method == "POST":
        action = request.form.get("action")

        # Bulk send
        if action == "bulk":
            template_id = int(request.form.get("template_id") or 0)
            tpl = get_sms_template(template_id) if template_id else None
            if not tpl:
                flash("Template select karo", "error")
                return redirect(url_for("sms.send"))

            # Get student list based on mode
            student_ids = request.form.getlist("student_ids")
            if not student_ids:
                flash("Koi student select nahi kiya", "error")
                return redirect(request.url)

            results = _send_bulk(student_ids, tpl, session["admin_id"])
            flash(f"{results['sent']} SMS sent, {results['failed']} failed",
                  "success" if results["failed"] == 0 else "warning")
            return redirect(url_for("sms.index"))

        # Single send (from log preview / manual)
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        student_id = request.form.get("student_id", type=int)
        if not phone or not message:
            flash("Phone aur message zaroori", "error")
            return redirect(url_for("sms.send"))

        res = sms_service.send_sms(phone, message)
        log_sms(
            student_id, phone, res.get("rendered_body", message),
            None, res.get("provider", "?"),
            res.get("message_id", ""),
            "sent" if res["ok"] else "failed",
            res.get("error", ""), session["admin_id"]
        )
        if res["ok"]:
            flash("SMS sent", "success")
        else:
            flash(f"SMS failed: {res.get('error', '')}", "error")
        return redirect(url_for("sms.index"))

    # GET — build preview list
    school = get_settings()
    students = []
    preselected = []

    if mode == "defaulters":
        month = request.args.get("month") or datetime.now().strftime("%Y-%m")
        students_raw = get_students_for_reminder(month, only_defaulters=True)
        students = [{"id": s["id"], "name": s["name"],
                     "class_name": s["class_name"], "section": s["section"],
                     "phone": s["phone"], "pending_fees": s["pending_fees"],
                     "month": month} for s in students_raw]
        preselected = [s["id"] for s in students]
    else:
        month = None
        for s in get_students():
            students.append({"id": s[0], "name": s[1],
                             "class_name": s[3], "section": s[4],
                             "phone": s[5], "pending_fees": 0,
                             "month": None})

    # Pre-render template preview for each student
    template_id = request.args.get("template_id", type=int)
    selected_template = get_sms_template(template_id) if template_id else (
        templates[0] if templates else None
    )

    # Auto-detect template based on mode
    if not template_id and templates:
        want_cat = {"defaulters": "fee", "absent": "attendance"}.get(mode)
        if want_cat:
            for t in templates:
                if t["category"] == want_cat:
                    selected_template = t
                    break

    # Build variables + rendered body per student
    for s in students:
        variables = {
            "name": s["name"] or "",
            "class": f"{s['class_name'] or ''}{('-' + s['section']) if s['section'] else ''}",
            "amount": f"{s.get('pending_fees', 0):.0f}",
            "month": s.get("month") or "",
            "school": school.get("school_name", "School"),
            "date": datetime.now().strftime("%d %b"),
        }
        s["variables"] = variables
        s["preview"] = sms_service._render_body(
            selected_template["body"] if selected_template else "", variables
        )

    return render_template("sms/send.html",
                           students=students,
                           templates=templates,
                           selected_template=selected_template,
                           mode=mode,
                           preselected=preselected,
                           month=month,
                           school=school)

def _send_bulk(student_ids, tpl, admin_id):
    """Send SMS to multiple students — loops with logging"""
    sent = 0
    failed = 0
    for sid_str in student_ids:
        try:
            sid = int(sid_str)
        except ValueError:
            continue
        row = get_student(sid)
        if not row:
            continue
        # row = id, name, roll_no, class_name, section, gender, dob, parent_name, parent_phone...
        phone = row[8] or ""
        name = row[1] or ""
        class_name = row[3] or ""

        # Determine variable values from pending fees etc.
        from database import get_student_fee_dues
        dues = get_student_fee_dues(sid)

        school = get_settings()
        variables = {
            "name": name,
            "class": class_name,
            "amount": f"{dues['pending']:.0f}",
            "month": dues["month"],
            "school": school.get("school_name", "School"),
            "date": datetime.now().strftime("%d %b"),
            "receipt": "",
            "exam": "",
        }

        # Skip if phone invalid
        if not sms_service._clean_phone(phone):
            log_sms(sid, phone, "", tpl["id"], "?", "", "failed",
                    "Invalid phone", admin_id)
            failed += 1
            continue

        res = sms_service.send_sms(
            phone, tpl["body"],
            template_id=tpl.get("msg91_template_id"),
            variables=variables
        )
        log_sms(
            sid, phone, res.get("rendered_body", ""),
            tpl["id"], res.get("provider", "?"),
            res.get("message_id", ""),
            "sent" if res["ok"] else "failed",
            res.get("error", ""), admin_id
        )
        if res["ok"]:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}

# ---------- Logs ----------
@sms_bp.route("/logs")
@login_required
@role_required("super_admin", "admin", "accountant")
def logs():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    items = get_sms_logs(limit=200, search=search or None, status=status or None)
    return render_template("sms/logs.html", logs=items,
                           search=search, selected_status=status)

# ---------- Templates management ----------
@sms_bp.route("/templates")
@login_required
@role_required("super_admin", "admin")
def templates_list():
    tpls = get_sms_templates(active_only=False)
    return render_template("sms/templates.html", templates=tpls)

@sms_bp.route("/templates/<int:tid>/update-id", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def template_update_id(tid):
    new_id = request.form.get("msg91_template_id", "").strip()
    update_sms_template_id(tid, new_id or None)
    flash("Template ID updated", "success")
    return redirect(url_for("sms.templates_list"))
