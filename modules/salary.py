from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    generate_salary_for_month, get_salary_records,
    get_salary_record, update_salary_adjustments,
    mark_salary_paid, delete_salary_record, get_salary_summary
)

salary_bp = Blueprint("salary", __name__, url_prefix="/salary")

@salary_bp.route("/")
@login_required
def index():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    status = request.args.get("status", "").strip()
    search = request.args.get("q", "").strip()

    records = get_salary_records(month, status or None, search or None)
    summary = get_salary_summary(month)
    return render_template("salary/index.html",
                           month=month, records=records, summary=summary,
                           selected_status=status, search=search)

@salary_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    month = request.form.get("month", "").strip()
    if not month:
        flash("Month missing", "error")
        return redirect(url_for("salary.index"))
    res = generate_salary_for_month(month)
    flash(
        f"{res['created']} records banaye, {res['skipped']} skip "
        f"(total staff: {res['total_staff']})", "success"
    )
    return redirect(url_for("salary.index", month=month))

@salary_bp.route("/<int:rid>/edit", methods=["GET", "POST"])
@login_required
def edit(rid):
    rec = get_salary_record(rid)
    if not rec:
        abort(404)
    if rec["status"] == "paid":
        flash("Paid record edit nahi ho sakta", "error")
        return redirect(url_for("salary.index", month=rec["month"]))

    if request.method == "POST":
        bonus = request.form.get("bonus") or 0
        deductions = request.form.get("deductions") or 0
        update_salary_adjustments(rid, bonus, deductions)
        flash("Adjustments update ho gaye", "success")
        return redirect(url_for("salary.index", month=rec["month"]))

    return render_template("salary/edit.html", rec=rec)

@salary_bp.route("/<int:rid>/pay", methods=["POST"])
@login_required
def pay(rid):
    rec = get_salary_record(rid)
    if not rec:
        abort(404)
    mode = request.form.get("mode") or "cash"
    note = request.form.get("note") or ""
    slip_no = mark_salary_paid(rid, mode, note, session["admin_id"])
    if slip_no:
        flash(f"Payment recorded — Slip {slip_no}", "success")
        return redirect(url_for("salary.slip", rid=rid))
    flash("Payment record nahi hua", "error")
    return redirect(url_for("salary.index", month=rec["month"]))

@salary_bp.route("/<int:rid>/slip")
@login_required
def slip(rid):
    rec = get_salary_record(rid)
    if not rec or rec["status"] != "paid":
        abort(404)
    return render_template("salary/slip.html", r=rec)

@salary_bp.route("/<int:rid>/delete", methods=["POST"])
@login_required
def remove(rid):
    rec = get_salary_record(rid)
    if rec:
        n = delete_salary_record(rid)
        if n:
            flash("Record delete", "success")
        else:
            flash("Sirf pending records delete ho sakte hain", "error")
    return redirect(url_for("salary.index", month=rec["month"] if rec else ""))
