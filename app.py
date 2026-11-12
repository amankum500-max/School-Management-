""" School Management System — Complete Application (Fully Connected) """
import os
import sys
import re
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from time import time as _time

sys.setrecursionlimit(2000)

from flask import (
    Flask, render_template, request, session, redirect, url_for,
    jsonify, Response, send_from_directory, send_file, g,
)
from flask_session import Session
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config

# ============================================================
# OPTIONAL IMPORTS — app crash न हो अगर package missing हो
# ============================================================
try:
    from google import genai as _genai
    _GENAI_AVAILABLE = True
except ImportError:
    _genai = None
    _GENAI_AVAILABLE = False

try:
    import bleach as _bleach
    _BLEACH_AVAILABLE = True
except ImportError:
    _bleach = None
    _BLEACH_AVAILABLE = False

# CSRF (optional — install करने पर auto-enable)
try:
    from flask_wtf import CSRFProtect
    _CSRF_AVAILABLE = True
except ImportError:
    CSRFProtect = None
    _CSRF_AVAILABLE = False


# ============================================================
# APP INITIALIZATION
# ============================================================
app = Flask(__name__)
app.config.from_object(Config)

# --- Proxy support (Nginx/Cloudflare के पीछे ज़रूरी) ---
if os.environ.get("TRUST_PROXY") == "1":
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1,
    )

_IS_PROD = os.environ.get("FLASK_ENV") == "production"

# --- Session + Upload hardening ---
app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
app.config.setdefault("SESSION_COOKIE_SECURE", _IS_PROD)
app.config.setdefault("MAX_CONTENT_LENGTH", 64 * 1024 * 1024)   # 64 MB
app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(hours=12))
app.config.setdefault("JSON_SORT_KEYS", False)

Session(app)

# --- CSRF: अगर flask-wtf installed है तो auto-enable ---
if _CSRF_AVAILABLE:
    CSRFProtect(app)

# --- AI client: सिर्फ तब बने जब key मौजूद हो ---
AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
ai_client = None
if _GENAI_AVAILABLE and os.environ.get("GEMINI_API_KEY"):
    try:
        ai_client = _genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    except Exception as e:
        app.logger.warning("AI client init failed: %s", e)


# ============================================================
# BLUEPRINT IMPORTS
# ============================================================
from modules.auth import auth_bp, login_required, role_required
from modules.students import students_bp
from modules.classes import classes_bp
from modules.fees import fees_bp
from modules.attendance import attendance_bp
from modules.notices import notices_bp
from modules.parent import parent_bp
from modules.exams import exams_bp
from modules.settings import settings_bp
from modules.staff import staff_bp
from modules.reports import reports_bp
from modules.bulk_import import bulk_bp
from modules.whatsapp import whatsapp_bp
from modules.backup import backup_bp
from modules.bills import bills_bp
from modules.id_card import id_card_bp
from modules.timetable import timetable_bp
from modules.salary import salary_bp
from modules.homework import homework_bp
from modules.transport import transport_bp
from modules.expenses import expenses_bp
from modules.certificates import certificates_bp
from modules.events import events_bp
from modules.library import library_bp
from modules.promotion import promotion_bp
from modules.teacher_portal import teacher_portal_bp
from modules.teachers_admin import teachers_admin_bp
from modules.medical import medical_bp
from modules.alerts import alerts_bp
from modules.admin_users import admin_users_bp
from modules.hostel import hostel_bp
from modules.qr_attendance import qr_attendance_bp
from modules.system import system_bp
from modules.annual_report import annual_report_bp
from modules.help import help_bp, get_help_slug
from modules.help_data import HELP_TOPICS
from modules.public import public_bp
from modules.admissions import admissions_bp
from modules.public_content import public_content_bp
from modules.payments import payments_bp
from modules.admin_payments import admin_payments_bp
from modules.staff_attendance import staff_att_bp
from modules.leave import leave_bp
from modules.discounts import discounts_bp
from modules.visitors import visitors_bp
from modules.advances import advances_bp
from modules.chat import chat_bp
from modules.online_exams import online_exams_bp
from modules.automation import automation_bp

# 👇 यहाँ सुधार किया गया है (hall_tickets_bp से hall_ticket_bp)
from modules.hall_tickets import hall_ticket_bp 

from modules.photos import photos_bp
from modules.report_cards import report_cards_bp
from modules.password_reset import password_reset_bp

# ============================================================
# REGISTER ALL BLUEPRINTS
# ============================================================
for _bp in (
    auth_bp, students_bp, classes_bp, fees_bp, attendance_bp, notices_bp,
    parent_bp, exams_bp, settings_bp, staff_bp, reports_bp, bulk_bp,
    whatsapp_bp, backup_bp, bills_bp, id_card_bp, timetable_bp, salary_bp,
    homework_bp, transport_bp, expenses_bp, certificates_bp, events_bp,
    library_bp, promotion_bp, teacher_portal_bp, teachers_admin_bp,
    medical_bp, alerts_bp, admin_users_bp, hostel_bp, qr_attendance_bp,
    system_bp, annual_report_bp, help_bp, public_bp, admissions_bp,
    public_content_bp, payments_bp, admin_payments_bp, staff_att_bp,
    leave_bp, discounts_bp, visitors_bp, advances_bp, chat_bp,
    online_exams_bp, automation_bp, 
    
    # 👇 यहाँ भी सुधार किया गया है (hall_tickets_bp से hall_ticket_bp)
    hall_ticket_bp, 
    
    photos_bp, report_cards_bp, password_reset_bp,
):
    app.register_blueprint(_bp)
del _bp


# ============================================================
# HELPERS
# ============================================================
_API_PREFIXES = (
    "/api", "/qr-attendance/mark", "/qr-attendance/summary",
    "/quick-search", "/notifications/count",
)

def _wants_json():
    if request.path.startswith(_API_PREFIXES):
        return True
    accept = request.accept_mimetypes
    best = accept.best if accept else None
    if not best:
        return False
    return best == "application/json" and accept[best] > accept["text/html"]

def _client_ip():
    if os.environ.get("TRUST_PROXY") == "1":
        return (request.headers.get("X-Forwarded-For") or request.remote_addr or "?")\
            .split(",")[0].strip()
    return request.remote_addr or "?"

def _sanitize_html(html: str) -> str:
    if not html:
        return ""
    if _BLEACH_AVAILABLE:
        allowed_tags = [
            "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr",
            "ul", "ol", "li", "strong", "b", "em", "i", "u",
            "table", "thead", "tbody", "tr", "th", "td",
            "div", "span", "section", "blockquote", "sub", "sup",
        ]
        allowed_attrs = {"*": ["class"], "table": ["border"]}
        return _bleach.clean(
            html, tags=allowed_tags, attributes=allowed_attrs, strip=True,
        )
    html = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<iframe\b[^<]*(?:(?!</iframe>)<[^<]*)*</iframe>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", html, flags=re.IGNORECASE)
    html = re.sub(r"javascript\s*:", "", html, flags=re.IGNORECASE)
    return html

def _require_ai():
    if ai_client is None:
        return jsonify({"error": "AI service not configured"}), 503
    return None

def _cached(key, fn):
    if not hasattr(g, key):
        setattr(g, key, fn())
    return getattr(g, key)


# ============================================================
# DIRECT ROUTES
# ============================================================
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/health")
def health_check():
    from database import get_conn
    status = {
        "status": "ok",
        "app": "School Management",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        status["database"] = "ok"
    except Exception as e:
        status["status"] = "degraded"
        status["database"] = "error"
        status["db_error"] = str(e)[:100]
        return jsonify(status), 503
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return jsonify(status), 200


@app.route("/dashboard")
@login_required
def dashboard():
    # 🛑 डेटाबेस फंक्शन्स को try-except में रखा गया है ताकि कोई भी फंक्शन मिसिंग होने पर पेज क्रैश न हो
    try:
        from database import (
            count_students, total_collected, today_attendance_percent,
            count_unread_notices, get_fees_monthly_trend, get_attendance_trend,
            get_students_by_class, count_new_enquiries, count_active_staff,
            count_homework_this_week, get_computed_alerts, get_custom_alerts,
            get_upcoming_events, count_upcoming_events, get_today_snapshot,
            get_month_fee_progress, get_birthdays_today, get_recent_activity,
            get_top_performers, get_class_attendance_today,
            get_staff_attendance_today_summary_dashboard as get_staff_attendance_today_summary,
            count_transport_students,
            get_visitors_summary_dashboard as get_visitors_summary,
            get_pending_leave_count, get_total_advance_outstanding,
        )
    except ImportError as e:
        return f"Database function missing error: {e}. Please check database.py", 500

    today_str = datetime.now().strftime("%Y-%m-%d")

    def safe(fn, default=None, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Dashboard DB Error in {fn.__name__}: {e}")
            return default

    return render_template(
        "dashboard.html",
        total_students=safe(count_students, 0),
        fees_collected=safe(total_collected, 0),
        attendance_today=safe(today_attendance_percent, None, today_str),
        recent_notices=safe(count_unread_notices, 0, 7),
        new_enquiries=safe(count_new_enquiries, 0),
        total_staff=safe(count_active_staff, 0),
        homework_week=safe(count_homework_this_week, 0),
        upcoming_events_count=safe(count_upcoming_events, 0, 7),
        fees_trend=safe(get_fees_monthly_trend, [], 6),
        att_trend=safe(get_attendance_trend, [], 7),
        class_dist=safe(get_students_by_class, []),
        computed_alerts=safe(get_computed_alerts, []),
        custom_alerts=safe(get_custom_alerts, [], True, 2),
        upcoming_events_list=safe(get_upcoming_events, [], 30, None, 5),
        today_snap=safe(get_today_snapshot, {}),
        fee_progress=safe(get_month_fee_progress, {}),
        birthdays=safe(get_birthdays_today, []),
        recent_activity=safe(get_recent_activity, [], 8),
        top_performers=safe(get_top_performers, {"exam": None, "students": []}, 5),
        class_att_bars=safe(get_class_attendance_today, []),
        staff_att_today=safe(get_staff_attendance_today_summary, {}),
        transport_students=safe(count_transport_students, 0),
        visitors_today=safe(get_visitors_summary, {}),
        pending_leave=safe(get_pending_leave_count, 0),
        advance_outstanding=safe(get_total_advance_outstanding, {"outstanding": 0, "active_count": 0}),
    )


# ============================================================
# NOTIFICATIONS ROUTES
# ============================================================
@app.route("/notifications")
@login_required
def notifications_page():
    from database import get_computed_alerts, get_custom_alerts
    try:
        computed = get_computed_alerts() or []
        custom = get_custom_alerts(active_only=True) or []
        all_notifs = []
        for c in computed:
            all_notifs.append({
                "title": c.get("title", "Alert"),
                "message": c.get("message", ""),
                "type": c.get("type", "info"),
                "icon": c.get("icon", "🔔"),
                "link": c.get("link", "#"),
                "severity": "high" if c.get("type") == "danger" else "medium",
            })
        for c in custom:
            all_notifs.append({
                "title": c.get("title", "Custom Alert"),
                "message": c.get("message", ""),
                "type": "info",
                "icon": "📢",
                "link": "#",
                "severity": "low",
            })
    except Exception as e:
        app.logger.warning("Error loading notifications: %s", e)
        all_notifs = []
    return render_template(
        "notifications.html",
        notifications={"items": all_notifs, "total": len(all_notifs)},
    )


@app.route("/notifications/count")
@login_required
def notifications_count_api():
    from database import get_computed_alerts, get_custom_alerts
    try:
        computed = get_computed_alerts() or []
        custom = get_custom_alerts(active_only=True) or []
        urgent = sum(1 for n in computed if n.get("type") == "danger")
        return jsonify({"count": len(computed) + len(custom), "urgent": urgent})
    except Exception:
        return jsonify({"count": 0, "urgent": 0})


@app.route("/quick-search")
@login_required
def quick_search_api():
    try:
        from database import quick_search
        q = request.args.get("q", "").strip()[:60]
        return jsonify(quick_search(q))
    except ImportError:
        return jsonify([])


@app.route("/manifest.json")
def manifest_route():
    from database import get_settings
    try:
        s = get_settings()
    except Exception:
        s = {"school_name": "School"}
    manifest = {
        "name": s.get("school_name", "School Management"),
        "short_name": (s.get("school_name", "School") or "School")[:12],
        "description": s.get("tagline", "School Management System"),
        "start_url": "/dashboard",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#f5f6fa",
        "theme_color": "#1e293b",
        "icons": [{
            "src": "/static/icon.svg",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable",
        }],
    }
    return jsonify(manifest)


@app.route("/sw.js")
def sw_route():
    resp = send_from_directory(app.static_folder, "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Content-Type"] = "application/javascript"
    return resp


# ============================================================
# AI ROUTES — SECURED
# ============================================================
@app.route("/api/ask-ai", methods=["POST"])
@login_required
def ask_ai():
    err = _require_ai()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    if len(user_message) > 2000:
        return jsonify({"error": "Message too long (max 2000 chars)"}), 400
    try:
        prompt = (
            "You are a helpful AI assistant for a School Management System. "
            "Keep your answers short, professional, and helpful.\n"
            f"Query: {user_message}"
        )
        response = ai_client.models.generate_content(
            model=AI_MODEL, contents=prompt,
        )
        return jsonify({"reply": (response.text or "").strip()})
    except Exception:
        app.logger.exception("ask_ai failed")
        return jsonify({"error": "AI service unavailable"}), 500


@app.route("/admin/generate-exam", methods=["GET", "POST"])
@login_required
@role_required("admin", "teacher")
def generate_exam():
    if request.method == "POST":
        err = _require_ai()
        if err:
            return err
        subject = (request.form.get("subject") or "").strip()[:100]
        grade = (request.form.get("grade") or "").strip()[:20]
        if not subject or not grade:
            return "Subject and Grade are required", 400
        prompt = f"""Create a school exam question paper for Class {grade}, Subject: {subject}.
Format it beautifully using HTML tags like <h4>, <ol>, <li>.
Do NOT use markdown like ```html. Just return the raw HTML.
Sections:
- Section A: 5 MCQs (1 mark each)
- Section B: 3 Short Questions (5 marks each)
- Section C: 2 Long Questions (10 marks each)"""
        try:
            response = ai_client.models.generate_content(
                model=AI_MODEL, contents=prompt,
            )
            raw = (response.text or "").replace("```html", "").replace("```", "").strip()
            clean_html = _sanitize_html(raw)
            return render_template(
                "exam_paper_result.html",
                exam_content=clean_html,
                subject=subject,
                grade=grade,
            )
        except Exception:
            app.logger.exception("generate_exam failed")
            return "AI service error — कृपया बाद में try करें", 500
    return render_template("generate_exam_form.html")


# ============================================================
# CONTEXT PROCESSORS (with per-request cache)
# ============================================================
@app.context_processor
def inject_school():
    from database import get_settings

    def _load():
        try:
            return get_settings()
        except Exception:
            return {"school_name": "School Management"}

    return {"school": _cached("_school_settings", _load)}


@app.context_processor
def inject_alert_count():
    if "admin_id" not in session:
        return {"alert_count": 0}

    def _load():
        try:
            from database import get_computed_alerts
            return len(get_computed_alerts())
        except Exception:
            return 0

    return {"alert_count": _cached("_alert_count", _load)}


@app.context_processor
def inject_chat_unread():
    if "admin_id" not in session:
        return {"chat_unread": 0}

    def _load():
        try:
            from database import count_unread_threads_for_admin
            return count_unread_threads_for_admin()
        except Exception:
            return 0

    return {"chat_unread": _cached("_chat_unread", _load)}


@app.context_processor
def inject_help_context():
    if "admin_id" not in session:
        return {"help_topic": None, "help_slug": None}
    slug = get_help_slug(request.path)
    topic = HELP_TOPICS.get(slug) if slug else None
    return {"help_topic": topic, "help_slug": slug}


# ============================================================
# ERROR HANDLERS — JSON aware, crash-proof
# ============================================================
@app.errorhandler(404)
def not_found(e):
    if _wants_json():
        return jsonify({"error": "not found"}), 404
    return render_template("errors/404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    if _wants_json():
        return jsonify({"error": "forbidden"}), 403
    return render_template("errors/403.html"), 403


@app.errorhandler(413)
def payload_too_large(e):
    msg = "File too large — अधिकतम size exceed हो गया"
    if _wants_json():
        return jsonify({"error": msg}), 413
    return msg, 413


@app.errorhandler(429)
def too_many_requests(e):
    msg = "Too many requests — thodi der baad try karo"
    if _wants_json():
        return jsonify({"error": msg}), 429
    return msg, 429


@app.errorhandler(500)
def server_error(e):
    app.logger.exception("Internal server error")
    if _wants_json():
        return jsonify({"error": "internal server error"}), 500
    return render_template("errors/500.html"), 500


@app.errorhandler(Exception)
def catch_all(e):
    if isinstance(e, HTTPException):
        if _wants_json():
            return jsonify({"error": e.description or e.name}), e.code or 500
        return e.get_response()
    app.logger.exception("Unhandled exception")
    if _wants_json():
        return jsonify({"error": "internal server error"}), 500
    return render_template("errors/500.html"), 500


# ============================================================
# BEFORE REQUEST — Thread-safe Rate Limiting
# ============================================================
_rate_store = defaultdict(list)
_rate_lock = threading.Lock()
_last_cleanup = _time()

# endpoint → (path_prefix, max_per_minute)
_SENSITIVE_PATHS = {
    "/login": 10,              
    "/parent/login": 10,
    "/teacher/login": 10,
    "/reset/": 10,
    "/api/ask-ai": 20,
    "/admin/generate-exam": 10,
    "/qr-attendance/mark": 300,
}


def _cleanup_rate_store():
    global _last_cleanup
    with _rate_lock:
        now = _time()
        if now - _last_cleanup < 300:
            return
        for k in list(_rate_store.keys()):
            _rate_store[k] = [t for t in _rate_store[k] if now - t < 60]
            if not _rate_store[k]:
                del _rate_store[k]
        _last_cleanup = now


def _rate_limit_check(ip, endpoint, max_per_minute=60):
    _cleanup_rate_store()
    now = _time()
    key = f"{ip}:{endpoint}"
    with _rate_lock:
        _rate_store[key] = [t for t in _rate_store[key] if now - t < 60]
        if len(_rate_store[key]) >= max_per_minute:
            return False
        _rate_store[key].append(now)
        return True


@app.before_request
def rate_limit_guard():
    path = request.path
    matched_limit = None
    for prefix, limit in _SENSITIVE_PATHS.items():
        if path.startswith(prefix):
            matched_limit = limit
            break
    if matched_limit is None:
        return None
    ip = _client_ip()
    if not _rate_limit_check(ip, path, matched_limit):
        if _wants_json():
            return jsonify({"error": "Too many requests — thodi der baad try karo"}), 429
        return "Too many requests — thodi der baad try karo", 429
    return None


# ============================================================
# AFTER REQUEST — Security, Cache, Audit
# ============================================================
@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
    if request.is_secure:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


@app.after_request
def cache_static(response):
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800"
    elif request.path in ("/sw.js", "/manifest.json"):
        response.headers["Cache-Control"] = "no-cache"
    if _wants_json():
        response.headers.setdefault("Vary", "Accept")
    return response


_AUDIT_EXCLUDE = (
    "/login", "/teacher/", "/parent/", "/site", "/reset/",
    "/alerts/log-send", "/pay/", "/automation/cron",
)

_ENTITY_MAP = {
    "/students/": "student", "/classes/": "classes", "/fees/": "fees",
    "/staff/": "staff", "/exams/": "exams", "/salary/": "salary",
    "/admin-users/": "admin_users", "/notices/": "notices",
    "/events/": "events", "/library/": "library", "/hostel/": "hostel",
    "/transport/": "transport", "/visitors/": "visitors",
    "/advances/": "advances", "/leave/": "leave", "/automation/": "automation",
}


@app.after_request
def auto_audit(response):
    try:
        if "admin_id" not in session:
            return response
        if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
            return response
        path = request.path
        if any(path.startswith(p) for p in _AUDIT_EXCLUDE):
            return response
        if not (200 <= response.status_code < 400):
            return response
        entity = next(
            (ent for prefix, ent in _ENTITY_MAP.items() if path.startswith(prefix)),
            None,
        )
        from database import log_audit
        try:
            log_audit(
                session["admin_id"],
                session.get("admin_username", "?"),
                action=f"{request.method} {path}",
                entity_type=entity,
                details=f"Path: {path}",
            )
        except TypeError:
            try:
                log_audit(
                    session["admin_id"],
                    f"{request.method} {path}",
                    entity or "",
                    f"Path: {path}",
                )
            except Exception as e2:
                app.logger.warning("Audit fallback also failed: %s", e2)
    except Exception as e:
        app.logger.warning("Audit Error: %s", e)
    return response


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )
