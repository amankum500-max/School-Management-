from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    generate_bills_for_class, get_bills, get_bill,
    delete_bills_for_month, get_bills_summary,
    check_bills_exist, get_classes_list
)

bills_bp = Blueprint("bills", __name__, url_prefix="/bills")

@bills_bp.route("/")
@login_required
def index():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    status = request.args.get("status", "").strip()
    class_name = request.args.get("class", "").strip()
    search = request.args.get("q", "").strip()

    bills = get_bills(month, status or None, class_name or None, search or None)
    summary = get_bills_summary(month)

    return render_template(
        "bills/index.html",
        month=month, bills=bills, summary=summary,
        selected_status=status, selected_class=class_name,
        search=search, classes=get_classes_list()
    )

@bills_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    if request.method == "POST":
        class_name = request.form.get("class_name", "").strip()
        month = request.form.get("month", "").strip()
        section = request.form.get("section", "").strip()

        if not class_name or not month:
            flash("Class aur month zaroori hain", "error")
            return redirect(url_for("bills.generate"))

        result = generate_bills_for_class(class_name, month, section or None)

        if result["error"]:
            flash(result["error"], "error")
            return redirect(url_for("bills.generate"))

        flash(
            f"{result['created']} bills create, {result['skipped']} skip "
            f"(total students: {result['total_students']}, per bill: ₹{result['total_amount']:.0f})",
            "success"
        )
        return redirect(url_for("bills.index", month=month, **{"class": class_name}))

    month_default = datetime.now().strftime("%Y-%m")
    return render_template("bills/generate.html",
                           classes=get_classes_list(),
                           month=month_default)

@bills_bp.route("/<int:bill_id>")
@login_required
def view(bill_id):
    b = get_bill(bill_id)
    if not b:
        abort(404)
    return render_template("bills/view.html", b=b)

@bills_bp.route("/<int:bill_id>/print")
@login_required
def print_bill(bill_id):
    b = get_bill(bill_id)
    if not b:
        abort(404)
    return render_template("bills/print.html", b=b)

@bills_bp.route("/delete-month", methods=["POST"])
@login_required
def delete_month():
    month = request.form.get("month", "").strip()
    class_name = request.form.get("class_name", "").strip() or None
    if not month:
        flash("Month missing", "error")
        return redirect(url_for("bills.index"))

    n = delete_bills_for_month(month, class_name)
    flash(f"{n} bills delete hue", "success")
    return redirect(url_for("bills.index", month=month))
    def generate_bills_for_class(class_name, month, section=None):
    """
    Class ke fee_structure se bills generate.
    Har student ke active discounts apply honge.
    Idempotent — existing bills skip.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Fee structure
    cur.execute("""
        SELECT fee_type, amount FROM fee_structure
        WHERE class_name=%s ORDER BY fee_type;
    """, (class_name,))
    items = [{"fee_type": r[0], "amount": float(r[1])} for r in cur.fetchall()]

    if not items:
        cur.close()
        conn.close()
        return {"created": 0, "skipped": 0, "error": "Fee structure nahi hai is class ka"}

    base_total = sum(item["amount"] for item in items)
    items_json = _json.dumps(items)

    # Students
    q = "SELECT id FROM students WHERE status='active' AND class_name=%s"
    params = [class_name]
    if section:
        q += " AND section=%s"
        params.append(section)
    cur.execute(q, tuple(params))
    student_ids = [r[0] for r in cur.fetchall()]

    created = 0
    skipped = 0
    total_discounted = 0.0
    for sid in student_ids:
        try:
            # Compute discount for this student
            discount_amount, discount_items = compute_student_discount(base_total, sid)
            final_total = max(base_total - discount_amount, 0)
            disc_json = _json.dumps(discount_items)

            cur.execute("""
                INSERT INTO bills
                (student_id, month, total_amount, base_amount,
                 discount_amount, discount_items, items, status)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, 'pending');
            """, (sid, month, final_total, base_total,
                  discount_amount, disc_json, items_json))
            created += 1
            total_discounted += discount_amount
        except Exception:
            skipped += 1
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    return {"created": created, "skipped": skipped, "error": None,
            "total_students": len(student_ids), "total_amount": base_total,
            "total_discounted": total_discounted}
    def get_bill(bill_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.student_id, b.month, b.total_amount,
               b.base_amount, b.discount_amount, b.discount_items,
               b.items, b.generated_at,
               s.name, s.roll_no, s.class_name, s.section,
               s.parent_name, s.parent_phone, s.address,
               COALESCE((SELECT SUM(amount) FROM fee_payments
                         WHERE student_id=b.student_id AND month=b.month), 0) AS paid
        FROM bills b
        JOIN students s ON s.id = b.student_id
        WHERE b.id=%s;
    """, (bill_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    items = row[8]
    if isinstance(items, str):
        items = _json.loads(items)
    discount_items = row[6]
    if isinstance(discount_items, str):
        discount_items = _json.loads(discount_items)
    return {
        "id": row[0], "student_id": row[1], "month": row[2],
        "total": float(row[3] or 0), "base": float(row[4] or 0),
        "discount": float(row[5] or 0), "discount_items": discount_items or [],
        "items": items or [],
        "generated_at": row[9], "student_name": row[10], "roll": row[11],
        "class_name": row[12], "section": row[13],
        "parent_name": row[14], "phone": row[15], "address": row[16],
        "paid": float(row[17] or 0)
    }
