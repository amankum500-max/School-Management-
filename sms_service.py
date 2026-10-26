"""
SMS service — supports MSG91 (India) and Twilio (fallback).
Handles DLT-compliant template-based sending.
"""
import os
import re
import requests

def _clean_phone(phone):
    """Strip everything, keep digits, ensure 10-digit India format"""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    # Strip +91 / 91 prefix
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""

def _render_body(body, variables):
    """Replace {key} placeholders"""
    out = body or ""
    for k, v in (variables or {}).items():
        out = out.replace("{" + str(k) + "}", str(v or ""))
    return out

# ---------- MSG91 ----------
def send_msg91(phone, body, template_id=None, variables=None):
    """
    Two modes:
    1. Template-based (DLT required): send with template_id + variables
    2. Plain text (only test mode with own number)
    """
    auth_key = os.getenv("MSG91_AUTH_KEY", "").strip()
    sender = os.getenv("MSG91_SENDER_ID", "SCHOOL").strip()
    route = os.getenv("MSG91_ROUTE", "4").strip()

    if not auth_key:
        return {"ok": False, "error": "MSG91_AUTH_KEY not set", "provider": "msg91"}

    phone10 = _clean_phone(phone)
    if not phone10:
        return {"ok": False, "error": "Invalid phone number", "provider": "msg91"}

    # Prefer template flow (DLT compliant)
    if template_id:
        url = "https://control.msg91.com/api/v5/flow/"
        payload = {
            "template_id": template_id,
            "sender": sender,
            "short_url": "0",
            "recipients": [
                {"mobiles": "91" + phone10, **(variables or {})}
            ]
        }
        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json"
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if r.status_code == 200 and data.get("type") == "success":
                return {
                    "ok": True,
                    "provider": "msg91",
                    "message_id": data.get("message", ""),
                    "response": data
                }
            return {
                "ok": False,
                "provider": "msg91",
                "error": data.get("message") or f"HTTP {r.status_code}",
                "response": data
            }
        except Exception as e:
            return {"ok": False, "provider": "msg91", "error": str(e)[:150]}

    # Plain-text fallback — only works in TEST mode for own verified number
    url = "https://control.msg91.com/api/v5/sms/"
    payload = {
        "sender": sender,
        "route": route,
        "country": "91",
        "sms": [{"message": body, "to": ["91" + phone10]}]
    }
    headers = {
        "authkey": auth_key,
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code == 200:
            return {"ok": True, "provider": "msg91",
                    "message_id": data.get("message", ""), "response": data}
        return {"ok": False, "provider": "msg91",
                "error": data.get("message") or f"HTTP {r.status_code}", "response": data}
    except Exception as e:
        return {"ok": False, "provider": "msg91", "error": str(e)[:150]}

# ---------- Twilio ----------
def send_twilio(phone, body):
    """Fallback international SMS"""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_num = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not (sid and token and from_num):
        return {"ok": False, "provider": "twilio", "error": "Twilio not configured"}

    phone10 = _clean_phone(phone)
    if not phone10:
        return {"ok": False, "provider": "twilio", "error": "Invalid phone"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        r = requests.post(
            url,
            auth=(sid, token),
            data={"From": from_num, "To": "+91" + phone10, "Body": body},
            timeout=15
        )
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code in (200, 201):
            return {"ok": True, "provider": "twilio",
                    "message_id": data.get("sid", ""), "response": data}
        return {"ok": False, "provider": "twilio",
                "error": data.get("message") or f"HTTP {r.status_code}", "response": data}
    except Exception as e:
        return {"ok": False, "provider": "twilio", "error": str(e)[:150]}

# ---------- Universal ----------
def send_sms(phone, body, template_id=None, variables=None):
    """
    Main entry point. Uses SMS_PROVIDER env var.
    Returns {ok, provider, message_id?, error?, rendered_body}
    """
    provider = os.getenv("SMS_PROVIDER", "msg91").lower().strip()
    rendered = _render_body(body, variables or {})

    if provider == "twilio":
        result = send_twilio(phone, rendered)
    else:
        result = send_msg91(phone, rendered, template_id=template_id,
                            variables=variables or {})
    result["rendered_body"] = rendered
    return result

def is_configured():
    provider = os.getenv("SMS_PROVIDER", "msg91").lower().strip()
    if provider == "twilio":
        return bool(os.getenv("TWILIO_ACCOUNT_SID") and
                    os.getenv("TWILIO_AUTH_TOKEN") and
                    os.getenv("TWILIO_FROM_NUMBER"))
    return bool(os.getenv("MSG91_AUTH_KEY"))
