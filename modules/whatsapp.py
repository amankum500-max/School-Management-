from datetime import datetime
from urllib.parse import quote
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify
)
from modules.auth import login_required
from database import (
    get_whatsapp_templates, get_whatsapp_template,
    create_whatsapp_template, update_whatsapp_template,
    delete_whatsapp_template, log_whatsapp,
    get_recent_whatsapp_logs, was_sent_recently,
    get_students_for_reminder, get_settings, get_classes_list
)

whatsapp_bp = Blueprint("whatsapp", __name__, url_prefix="/whatsapp")

def _render_message(template_body, student, month, school_name):
    """Placeholder replace"""
    return (template_body
            .replace("{name}", student["name"] or "")
            .replace("{parent}", student.get("parent_name") or "Parent")
            .replace("{class}", f"{student.get('class_name') or ''}"
                               f"{('-' + student['section']) if student.get('section') else ''}")
            .replace("{roll}", student.get("roll") or "")
            .replace("{month}", month)
            .replace("{amount}", f"{student.get('pending_fees', 0):.0f}")
            .replace("{school}", school_name))

@whatsapp_bp.route("/")
@login_required
def index():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    category = request.args.get("category", "").strip()
    class_name = request.args.get("class", "").strip()
    mode = request.args.get("mode", "defaulters")   # defaulters | low_att | all
    template_id = request.args.get("template_id", type=int)

    templates = get_whatsapp_templates()

    # auto-select template based on mode
    if not template_id and templates:
        for t in templates:
            if mode == "defaulters" and t["category"] == "fee":
                template_id = t["id"]; break
            if mode == "low_att" and t["category"] == "attendance":
                template_id = t["id"]; break
        if not template_id:
            template_id = templates[0]["id"]

    selected_template = get_whatsapp_template(template_id) if template_id else None

    # fetch students
    only_defaulters = (mode == "defaulters")
    min_att = 75 if mode == "low_att" else None
    students = get_students_for_reminder(
        month, min_att_percent=min_att,
        only_defaulters=only_defaulters,
        class_name=class_name or None
    )

    # prepare messages
    school = get_settings()
    school_name = school.get("school_name", "School")

    prepared = []
    for s in students:
        msg = _render_message(
            selected_template["body"] if selected_template else "",
            s, month, school_name
        )
        phone = (s.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
        # recent sent check
        recent_sent = None
        if selected_template:
            recent_sent = was_sent_recently(s["id"], selected_template["id"], days=7)

        prepared.append({
            **s,
            "phone_clean": phone,
            "message": msg,
            "message_encoded": quote(msg),
            "recent_sent": recent_sent
        })

    return render_template(
        "whatsapp/index.html",
        month=month,
        mode=mode,
        category=category,
        selected_class=class_name,
        classes=get_classes_list(),
        templates=templates,
        selected_template=selected_template,
        students=prepared
    )

@whatsapp_bp.route("/log", methods=["POST"])
@login_required
def log_send():
    data = request.json or {}
    student_id = data.get("student_id")
    template_id = data.get("template_id")
    phone = data.get("phone", "")
    message = data.get("message", "")
    if not student_id or not phone:
        return jsonify({"ok": False}), 400
    log_whatsapp(student_id, template_id, phone, message, session["admin_id"])
    return jsonify({"ok": True})

@whatsapp_bp.route("/history")
@login_required
def history():
    logs = get_recent_whatsapp_logs(limit=200)
    return render_template("whatsapp/history.html", logs=logs)

# ---------- Templates management ----------
@whatsapp_bp.route("/templates")
@login_required
def templates_list():
    return render_template(
        "whatsapp/templates.html",
        templates=get_whatsapp_templates()
    )

@whatsapp_bp.route("/templates/add", methods=["GET", "POST"])
@login_required
def template_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "custom")
        body = request.form.get("body", "").strip()
        if not name or not body:
            flash("Name aur body zaroori hain", "error")
            return redirect(url_for("whatsapp.template_add"))
        create_whatsapp_template(name, category, body)
        flash("Template create ho gaya", "success")
        return redirect(url_for("whatsapp.templates_list"))
    return render_template("whatsapp/template_form.html",
                           template=None, mode="add")

@whatsapp_bp.route("/templates/<int:tid>/edit", methods=["GET", "POST"])
@login_required
def template_edit(tid):
    t = get_whatsapp_template(tid)
    if not t:
        flash("Template nahi mila", "error")
        return redirect(url_for("whatsapp.templates_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "custom")
        body = request.form.get("body", "").strip()
        if not name or not body:
            flash("Name aur body zaroori hain", "error")
            return redirect(url_for("whatsapp.template_edit", tid=tid))
        update_whatsapp_template(tid, name, category, body)
        flash("Template update ho gaya", "success")
        return redirect(url_for("whatsapp.templates_list"))

    return render_template("whatsapp/template_form.html",
                           template=t, mode="edit")

@whatsapp_bp.route("/templates/<int:tid>/delete", methods=["POST"])
@login_required
def template_delete(tid):
    delete_whatsapp_template(tid)
    flash("Template delete ho gaya", "success")
    return redirect(url_for("whatsapp.templates_list"))
