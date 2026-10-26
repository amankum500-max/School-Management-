from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, abort
)
from modules.parent import parent_required
from database import (
    get_student, get_children_for_parent,
    create_online_payment, get_online_payment_by_order,
    mark_online_payment_success, mark_online_payment_failed,
    get_student_fee_dues, create_fee_payment,
    get_online_payments_for_student
)
import razorpay_gateway as rp

payments_bp = Blueprint("payments", __name__, url_prefix="/pay")

@payments_bp.route("/start/<int:student_id>")
@parent_required
def start(student_id):
    """Parent ke liye — amount check karke order create"""
    # Verify student belongs to parent
    children = get_children_for_parent(session["parent_phone"])
    if student_id not in [c["id"] for c in children]:
        abort(403)

    student_row = get_student(student_id)
    if not student_row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, student_row))

    dues = get_student_fee_dues(student_id)
    if dues["pending"] <= 0:
        flash("Koi fees pending nahi hai", "success")
        return redirect(url_for("parent.child_detail", student_id=student_id))

    # Amount from query (parent can pay partial) or full pending
    try:
        amount = float(request.args.get("amount") or dues["pending"])
    except ValueError:
        amount = dues["pending"]
    amount = min(amount, dues["pending"])
    if amount < 1:
        flash("Amount minimum ₹1 hona chahiye", "error")
        return redirect(url_for("parent.child_detail", student_id=student_id))

    # Create Razorpay order
    try:
        receipt = f"OP-{student_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order = rp.create_order(
            amount,
            receipt,
            notes={"student_id": str(student_id), "month": dues["month"],
                   "name": student["name"]}
        )
    except Exception as e:
        flash(f"Payment gateway error: {str(e)[:100]}", "error")
        return redirect(url_for("parent.child_detail", student_id=student_id))

    # Save record
    local_pid = create_online_payment(
        student_id, amount, dues["month"], "fees",
        order["id"], note=f"Online payment attempt"
    )

    return render_template(
        "payments/checkout.html",
        student=student,
        order=order,
        dues=dues,
        amount=amount,
        razorpay_key=rp.get_public_key(),
        local_pid=local_pid
    )

@payments_bp.route("/verify", methods=["POST"])
@parent_required
def verify():
    """AJAX endpoint — payment success verify + create fee_payment entry"""
    data = request.json or {}
    order_id = data.get("razorpay_order_id", "").strip()
    payment_id = data.get("razorpay_payment_id", "").strip()
    signature = data.get("razorpay_signature", "").strip()

    if not (order_id and payment_id and signature):
        return jsonify({"ok": False, "error": "Missing payment details"}), 400

    # Signature verification (CRITICAL — never skip)
    if not rp.verify_signature(order_id, payment_id, signature):
        return jsonify({"ok": False, "error": "Signature verification failed"}), 400

    # Get local record
    op = get_online_payment_by_order(order_id)
    if not op:
        return jsonify({"ok": False, "error": "Order not found"}), 404
    if op["status"] == "paid":
        return jsonify({"ok": True, "already": True,
                        "payment_id": op["payment_id"]})

    # Create fee_payment entry (linked)
    try:
        result = create_fee_payment(
            op["student_id"], "Fees", op["amount"], op["month"],
            "online", f"Razorpay: {payment_id}", session.get("parent_id")
        )
        fee_payment_id = result["id"]
        receipt_no = result["receipt_no"]
    except Exception as e:
        return jsonify({"ok": False, "error": f"DB error: {str(e)[:80]}"}), 500

    # Mark success
    mark_online_payment_success(order_id, payment_id, signature, fee_payment_id)

    return jsonify({
        "ok": True,
        "payment_id": payment_id,
        "receipt_no": receipt_no,
        "fee_payment_id": fee_payment_id,
        "amount": op["amount"]
    })

@payments_bp.route("/failed", methods=["POST"])
@parent_required
def failed():
    data = request.json or {}
    order_id = data.get("order_id", "").strip()
    reason = data.get("reason", "")[:200]
    if order_id:
        mark_online_payment_failed(order_id, reason)
    return jsonify({"ok": True})

@payments_bp.route("/success/<int:student_id>")
@parent_required
def success(student_id):
    """Post-payment success page"""
    children = get_children_for_parent(session["parent_phone"])
    if student_id not in [c["id"] for c in children]:
        abort(403)

    student_row = get_student(student_id)
    if not student_row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, student_row))

    history = get_online_payments_for_student(student_id, limit=10)
    return render_template("payments/success.html",
                           student=student, history=history)

# ---------- Webhook (for server-to-server reliability) ----------
@payments_bp.route("/webhook", methods=["POST"])
def webhook():
    """Razorpay webhook — payment.captured events"""
    import hmac as _hmac
    import hashlib as _hashlib
    import os

    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    received_sig = request.headers.get("X-Razorpay-Signature", "")
    body = request.get_data()

    if webhook_secret:
        expected = _hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            _hashlib.sha256
        ).hexdigest()
        if not _hmac.compare_digest(expected, received_sig):
            return jsonify({"ok": False, "error": "Invalid webhook signature"}), 401

    try:
        import json as _json
        payload = _json.loads(body)
        event = payload.get("event", "")

        if event == "payment.captured":
            entity = payload["payload"]["payment"]["entity"]
            payment_id = entity["id"]
            order_id = entity.get("order_id")
            if order_id:
                op = get_online_payment_by_order(order_id)
                if op and op["status"] != "paid":
                    # Create fee entry + mark success
                    try:
                        result = create_fee_payment(
                            op["student_id"], "Fees", op["amount"],
                            op["month"], "online",
                            f"Razorpay webhook: {payment_id}", None
                        )
                        mark_online_payment_success(
                            order_id, payment_id, "", result["id"]
                        )
                    except Exception:
                        pass
    except Exception:
        pass

    return jsonify({"ok": True}), 200
