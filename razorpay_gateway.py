import os
import hmac
import hashlib
import razorpay

_client = None

def get_client():
    global _client
    if _client is None:
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        if not key_id or not key_secret:
            raise RuntimeError("Razorpay keys not set in environment")
        _client = razorpay.Client(auth=(key_id, key_secret))
    return _client

def get_public_key():
    return os.getenv("RAZORPAY_KEY_ID", "")

def create_order(amount_rupees, receipt_no, notes=None):
    """
    amount_rupees: amount in rupees (e.g. 1500)
    Returns: dict with id, amount (in paise), currency, etc.
    """
    client = get_client()
    order_data = {
        "amount": int(amount_rupees * 100),    # paise
        "currency": "INR",
        "receipt": (receipt_no or "")[:40],
        "payment_capture": 1,    # auto capture
        "notes": notes or {}
    }
    return client.order.create(data=order_data)

def verify_signature(order_id, payment_id, signature):
    """Verify Razorpay webhook/checkout signature"""
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not key_secret:
        return False
    expected = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")

def fetch_payment(payment_id):
    """Fetch actual payment details from Razorpay"""
    client = get_client()
    return client.payment.fetch(payment_id)
