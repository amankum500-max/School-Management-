from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    get_fee_structures, create_fee_structure, delete_fee_structure,
    create_fee_payment, get_payment, get_payments, delete_payment,
    total_collected, get_defaulters, pending_amount_for_student,
    get_student, get_students, get_classes_list
)

fees_bp = Blueprint("fees", __name__, url_prefix="/fees")

@fees_bp.route("/")
@login_required
def index():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    payments = get_payments(month=month, limit=100)
    return render_template(
        "fees/index.html",
        month=month,
        payments=[
            {"id": r[0], "student_id": r[1], "student": r[2],
             "class_name": r[3], "section": r[4], "fee_type": r[5],
             "amount": r[6], "month": r[7], "mode": r[8],
             "receipt_no": r[9], "paid_at": r[10]}
            for r in payments
        ],
        total=total_collected(month),
        total_all=total_collected()
    )

# ---------- Fee Structure ----------
@fees_bp.route("/structure", methods=["GET", "POST"])
@login_required
def structure():
    if request.method == "POST":
        data = request.form
        try:
            create_fee_structure(
                data["class_name"], data["fee_type"],
                float(data["amount"]), data.get("frequency") or "monthly"
            )
            flash("Fee structure add ho gaya", "success")
        except Exception as e:
            flash(f"Error: {e}", "error")
        return redirect(url_for("fees.structure"))

    selected = request.args.get("class", "").strip()
    rows = get_fee_structures(selected or None)
    return render_template(
        "fees/structure.html",
        items=[
            {"id": r[0], "class_name": r[1], "fee_type": r[2],
             "amount": r[3], "frequency": r[4]}
            for r in rows
        ],
        classes=get_classes_list(),
        selected_class=selected
    )

@fees_bp.route("/structure/<int:fid>/delete", methods=["POST"])
@login_required
def structure_delete(fid):
    delete_fee_structure(fid)
    flash("Structure entry delete", "success")
    return redirect(url_for("fees.structure"))

# ---------- Collect ----------
@fees_bp.route("/collect", methods=["GET", "POST"])
@login_required
def collect():
    if request.method == "POST":
        data = request.form
        try:
            res = create_fee_payment(
                int(data["student_id"]), data["fee_type"],
                float(data["amount"]), data["month"],
                data.get("mode") or "cash", data.get("note") or "",
                session["admin_id"]
            )
            flash(f"Payment recorded — Receipt {res['receipt_no']}", "success")
            return redirect(url_for("fees.receipt", payment_id=res["id"]))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("fees.collect"))

    month = datetime.now().strftime("%Y-%m")
    return render_template(
        "fees/collect.html",
        students=[{"id": r[0], "name": r[1], "roll": r[2],
                   "class_name": r[3], "section": r[4]} for r in get_students()],
        month=month
    )

# ---------- Receipt ----------
@fees_bp.route("/receipt/<int:payment_id>")
@login_required
def receipt(payment_id):
    r = get_payment(payment_id)
    if not r:
        abort(404)
    keys = ["id","student_id","fee_type","amount","month","mode",
            "receipt_no","note","paid_at","student_name","roll_no",
            "class_name","section","parent_name","parent_phone"]
    payment = dict(zip(keys, r))
    return render_template("fees/receipt.html", p=payment)

# ---------- Defaulters ----------
@fees_bp.route("/defaulters")
@login_required
def defaulters():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    rows = get_defaulters(month)
    return render_template(
        "fees/defaulters.html",
        month=month,
        rows=[
            {"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3],
             "section": r[4], "phone": r[5],
             "due": r[6], "paid": r[7], "pending": r[6]-r[7]}
            for r in rows
        ],
        total_pending=sum(r[6]-r[7] for r in rows)
    )

# ---------- Delete payment ----------
@fees_bp.route("/payment/<int:pid>/delete", methods=["POST"])
@login_required
def payment_delete(pid):
    delete_payment(pid)
    flash("Payment delete", "success")
    return redirect(url_for("fees.index"))
