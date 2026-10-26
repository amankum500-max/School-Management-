from flask import Blueprint, render_template, request
from modules.auth import login_required, role_required
from database import get_online_payments_summary, get_conn
from datetime import datetime

admin_payments_bp = Blueprint("admin_payments", __name__,
                              url_prefix="/admin/payments")

@admin_payments_bp.route("/")
@login_required
@role_required("super_admin", "admin", "accountant")
def index():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")

    summary = get_online_payments_summary(month)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT op.id, op.amount, op.month, op.purpose,
               op.razorpay_payment_id, op.status, op.paid_at,
               s.name, s.roll_no, s.class_name, s.section
        FROM online_payments op
        JOIN students s ON s.id = op.student_id
        WHERE op.status='paid' AND op.month=%s
        ORDER BY op.paid_at DESC;
    """, (month,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    payments = [{"id": r[0], "amount": float(r[1] or 0), "month": r[2],
                 "purpose": r[3], "payment_id": r[4], "status": r[5],
                 "paid_at": r[6], "student_name": r[7], "roll": r[8],
                 "class_name": r[9], "section": r[10]} for r in rows]

    return render_template("admin_payments/index.html",
                           summary=summary, payments=payments, month=month)
