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
