from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from urllib.parse import quote
from modules.auth import login_required
from database import (
    create_notice, get_notices, get_notice,
    update_notice, delete_notice, get_classes_list,
    students_phone_list
)

notices_bp = Blueprint("notices", __name__, url_prefix="/notices")

@notices_bp.route("/")
@login_required
def index():
    cat = request.args.get("category", "").strip()
    rows = get_notices(public_only=False, category=cat or None)
    notices = [
        {"id": r[0], "title": r[1], "content": r[2], "category": r[3],
         "priority": r[4], "target_class": r[5], "is_public": r[6],
         "published": r[7], "created_at": r[8]}
        for r in rows
    ]
    return render_template(
        "notices/index.html",
        notices=notices,
        selected_category=cat
    )

@notices_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        nid = create_notice(request.form.to_dict(), session["admin_id"])
        flash("Notice publish ho gaya", "success")
        return redirect(url_for("notices.view", notice_id=nid))
    return render_template("notices/form.html",
                           notice=None, mode="add",
                           classes=get_classes_list())

@notices_bp.route("/<int:notice_id>")
@login_required
def view(notice_id):
    row = get_notice(notice_id)
    if not row:
        abort(404)
    keys = ["id","title","content","category","priority","target_class",
            "is_public","published","created_at"]
    notice = dict(zip(keys, row))
    return render_template("notices/view.html", notice=notice)

@notices_bp.route("/<int:notice_id>/edit", methods=["GET", "POST"])
@login_required
def edit(notice_id):
    row = get_notice(notice_id)
    if not row:
        abort(404)
    keys = ["id","title","content","category","priority","target_class",
            "is_public","published","created_at"]
    notice = dict(zip(keys, row))

    if request.method == "POST":
        update_notice(notice_id, request.form.to_dict())
        flash("Notice update ho gaya", "success")
        return redirect(url_for("notices.view", notice_id=notice_id))

    return render_template("notices/form.html",
                           notice=notice, mode="edit",
                           classes=get_classes_list())

@notices_bp.route("/<int:notice_id>/delete", methods=["POST"])
@login_required
def remove(notice_id):
    delete_notice(notice_id)
    flash("Notice delete ho gaya", "success")
    return redirect(url_for("notices.index"))

# ---------- WhatsApp broadcast ----------
@notices_bp.route("/<int:notice_id>/whatsapp")
@login_required
def whatsapp_broadcast(notice_id):
    row = get_notice(notice_id)
    if not row:
        abort(404)
    notice = {"title": row[1], "content": row[2]}
    class_name = request.args.get("class", "").strip()

    # Base message
    msg = f"*{notice['title']}*\n\n{notice['content']}\n\n— School Management"
    msg_encoded = quote(msg)

    students = students_phone_list(class_name or None)
    return render_template(
        "notices/whatsapp.html",
        notice=notice,
        msg_encoded=msg_encoded,
        students=[
            {"name": r[0], "phone": r[1], "class_name": r[2], "section": r[3]}
            for r in students
        ],
        selected_class=class_name,
        classes=get_classes_list()
    )

# ---------- Public notice board ----------
@notices_bp.route("/public")
def public_board():
    rows = get_notices(public_only=True)
    notices = [
        {"id": r[0], "title": r[1], "content": r[2], "category": r[3],
         "priority": r[4], "created_at": r[8]}
        for r in rows
    ]
    return render_template("notices/public.html", notices=notices)
