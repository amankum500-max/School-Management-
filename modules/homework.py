from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    create_homework, get_homework_list, get_homework,
    update_homework, delete_homework, get_classes_list
)

homework_bp = Blueprint("homework", __name__, url_prefix="/homework")

@homework_bp.route("/")
@login_required
def index():
    class_name = request.args.get("class", "").strip()
    subject = request.args.get("subject", "").strip()
    search = request.args.get("q", "").strip()

    items = get_homework_list(
        class_name=class_name or None,
        subject=subject or None,
        search=search or None
    )
    today = date.today()

    for h in items:
        if h["due_date"]:
            if h["due_date"] < today:
                h["status"] = "overdue"
            elif h["due_date"] == today:
                h["status"] = "today"
            else:
                h["status"] = "upcoming"
        else:
            h["status"] = "no_due"

    return render_template(
        "homework/index.html",
        items=items,
        selected_class=class_name,
        subject=subject, search=search,
        classes=get_classes_list()
    )

@homework_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("class_name") or not data.get("subject") or not data.get("title"):
            flash("Class, subject, title zaroori hain", "error")
            return redirect(url_for("homework.add"))
        hid = create_homework(data, session["admin_id"])
        flash("Homework create ho gaya", "success")
        return redirect(url_for("homework.view", hid=hid))
    return render_template("homework/form.html",
                           h=None, mode="add",
                           classes=get_classes_list())

@homework_bp.route("/<int:hid>")
@login_required
def view(hid):
    h = get_homework(hid)
    if not h:
        abort(404)
    today = date.today()
    if h["due_date"]:
        if h["due_date"] < today:
            h["status"] = "overdue"
        elif h["due_date"] == today:
            h["status"] = "today"
        else:
            h["status"] = "upcoming"
    else:
        h["status"] = "no_due"
    return render_template("homework/view.html", h=h)

@homework_bp.route("/<int:hid>/edit", methods=["GET", "POST"])
@login_required
def edit(hid):
    h = get_homework(hid)
    if not h:
        abort(404)
    if request.method == "POST":
        data = request.form.to_dict()
        update_homework(hid, data)
        flash("Homework update ho gaya", "success")
        return redirect(url_for("homework.view", hid=hid))
    return render_template("homework/form.html",
                           h=h, mode="edit",
                           classes=get_classes_list())

@homework_bp.route("/<int:hid>/delete", methods=["POST"])
@login_required
def remove(hid):
    delete_homework(hid)
    flash("Homework delete ho gaya", "success")
    return redirect(url_for("homework.index"))
