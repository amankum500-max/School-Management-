from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    create_advance, get_advance, get_advances, get_active_advance,
    get_advance_repayments, record_advance_repayment, cancel_advance,
    get_staff_advances_summary, get_total_advance_outstanding,
    get_staff, get_staff_list, ADVANCE_TYPES
)

advances_bp = Blueprint("advances", __name__, url_prefix="/advances")


@advances_bp.route("/")
@login_required
@role_required("super_admin", "admin", "accountant")
def index():
    status = request.args.get("status", "").strip() or "active"
    staff_id = request.args.get("staff_id", type=int)
    items = get_advances(status=status or None, staff_id=staff_id)
    summary = get_total_advance_outstanding()
    return render_template("advances/index.html",
                           advances=items, summary=summary,
                           selected_status=status,
                           selected_staff=staff_id,
                           staff_list=get_staff_list())


@advances_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin", "accountant")
def new():
    if request.method == "POST":
        try:
            staff_id = int(request.form["staff_id"])
            advance_type = request.form.get("advance_type", "advance")
            total = float(request.form["total_amount"])
            monthly = float(request.form["monthly_deduction"])
            start_month = request.form["start_month"]
            reason = request.form.get("reason", "")

            aid = create_advance(
                staff_id, advance_type, total, monthly,
                start_month, reason, session["admin_id"]
            )
            flash("Advance create ho gaya", "success")
            return redirect(url_for("advances.detail", adv_id=aid))
        except Exception as e:
            flash(f"Error: {str(e)[:150]}", "error")
            return redirect(url_for("advances.new"))

    staff_list = get_staff_list()
    return render_template("advances/form.html",
                           staff_list=staff_list,
                           advance_types=ADVANCE_TYPES,
                           today_month=datetime.now().strftime("%Y-%m"))


@advances_bp.route("/<int:adv_id>")
@login_required
@role_required("super_admin", "admin", "accountant")
def detail(adv_id):
    a = get_advance(adv_id)
    if not a:
        abort(404)
    repayments = get_advance_repayments(adv_id)
    return render_template("advances/detail.html",
                           a=a, repayments=repayments)


@advances_bp.route("/<int:adv_id>/cancel", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def cancel(adv_id):
    if cancel_advance(adv_id):
        flash("Advance cancelled", "success")
    else:
        flash("Cancel fail — already closed/cancelled", "error")
    return redirect(url_for("advances.detail", adv_id=adv_id))


@advances_bp.route("/<int:adv_id>/manual-repay", methods=["POST"])
@login_required
@role_required("super_admin", "admin", "accountant")
def manual_repay(adv_id):
    a = get_advance(adv_id)
    if not a:
        abort(404)
    try:
        month = request.form["month"]
        amount = float(request.form["amount"])
        if record_advance_repayment(adv_id, month, amount):
            flash(f"Repayment ₹{amount:.0f} recorded for {month}", "success")
        else:
            flash("Repayment already exists for this month", "error")
    except Exception as e:
        flash(f"Error: {str(e)[:150]}", "error")
    return redirect(url_for("advances.detail", adv_id=adv_id))


@advances_bp.route("/staff/<int:staff_id>")
@login_required
@role_required("super_admin", "admin", "accountant")
def staff_view(staff_id):
    m = get_staff(staff_id)
    if not m:
        abort(404)
    summary = get_staff_advances_summary(staff_id)
    advances_list = get_advances(staff_id=staff_id, status=None)
    return render_template("advances/staff_view.html",
                           m=m, summary=summary,
                           advances=advances_list)
