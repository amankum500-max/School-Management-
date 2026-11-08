"""
School Management System — Complete Application (Fully Connected)
"""

import os
import sys
from datetime import datetime

# रिकर्सन लिमिट बढ़ा दी है ताकि कोई इंटरनल एरर न आए
sys.setrecursionlimit(2000)

from flask import (
    Flask, render_template, request, session,
    redirect, url_for, jsonify, Response, send_from_directory, send_file
)
from flask_session import Session
from werkzeug.exceptions import HTTPException

from config import Config

# --- NAYA GOOGLE GENAI SETUP ---
from google import genai
# नया AI Client सेटअप
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
# -------------------------------

from PIL import Image

# ============================================================
# APP INITIALIZATION
# ============================================================
app = Flask(__name__)
app.config.from_object(Config)
Session(app)

# ============================================================
# BLUEPRINT IMPORTS
# ============================================================
# Phase 1 — Auth
from modules.auth import auth_bp, login_required, role_required

# Phase 2-8 — Core Modules
from modules.students import students_bp
from modules.classes import classes_bp  # <--- YEH NAYA ADD KIYA HAI
from modules.fees import fees_bp
from modules.attendance import attendance_bp
from modules.exams import exams_bp
from modules.notices import notices_bp
from modules.parent import parent_bp
from modules.settings import settings_bp
from modules.staff import staff_bp

# Phase 9-17 — Reports, Bulk, WhatsApp, Backup, Bills, ID Card
from modules.reports import reports_bp
from modules.bulk_import import bulk_bp
from modules.whatsapp import whatsapp_bp
from modules.backup import backup_bp
from modules.bills import bills_bp
from modules.id_card import id_card_bp

# Phase 18-25 — Timetable, Salary, Homework, Transport, Expenses, Certificates, Events, Library
from modules.timetable import timetable_bp
from modules.salary import salary_bp
from modules.homework import homework_bp
from modules.transport import transport_bp
from modules.expenses import expenses_bp
from modules.certificates import certificates_bp
from modules.events import events_bp
from modules.library import library_bp

# Phase 26-32 — Promotion, Teacher Portal, Medical, Alerts, Admin Users, Hostel, QR
from modules.promotion import promotion_bp
from modules.teacher_portal import teacher_portal_bp
from modules.teachers_admin import teachers_admin_bp
from modules.medical import medical_bp
from modules.alerts import alerts_bp
from modules.admin_users import admin_users_bp
from modules.hostel import hostel_bp
from modules.qr_attendance import qr_attendance_bp

# Phase 33-37 — System, Annual Report, Help, Public Site, Admissions, Payments
from modules.system import system_bp
from modules.annual_report import annual_report_bp
from modules.help import help_bp, get_help_slug
from modules.help_data import HELP_TOPICS
from modules.public import public_bp
from modules.admissions import admissions_bp
from modules.public_content import public_content_bp
from modules.payments import payments_bp
from modules.admin_payments import admin_payments_bp

# Phase 39-51 — Staff Attendance, Leave, Discounts, Visitors, Advances, Chat, Online Exams...
from modules.staff_attendance import staff_att_bp
from modules.leave import leave_bp
from modules.discounts import discounts_bp
from modules.visitors import visitors_bp
from modules.advances import advances_bp
from modules.chat import chat_bp
from modules.online_exams import online_exams_bp
from modules.automation import automation_bp
from modules.hall_tickets import hall_tickets_bp
from modules.photos import photos_bp
from modules.report_cards import report_cards_bp
from modules.password_reset import password_reset_bp


# ============================================================
# REGISTER ALL BLUEPRINTS
# ============================================================
app.register_blueprint(auth_bp)
app.register_blueprint(students_bp)
app.register_blueprint(classes_bp)  # <--- YEH NAYA ADD KIYA HAI
app.register_blueprint(fees_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(exams_bp)
app.register_blueprint(notices_bp)
app.register_blueprint(parent_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(bulk_bp)
app.register_blueprint(whatsapp_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(bills_bp)
app.register_blueprint(id_card_bp)
app.register_blueprint(timetable_bp)
app.register_blueprint(salary_bp)
app.register_blueprint(homework_bp)
app.register_blueprint(transport_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(certificates_bp)
app.register_blueprint(events_bp)
app.register_blueprint(library_bp)
app.register_blueprint(promotion_bp)
app.register_blueprint(teacher_portal_bp)
app.register_blueprint(teachers_admin_bp)
app.register_blueprint(medical_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(admin_users_bp)
app.register_blueprint(hostel_bp)
app.register_blueprint(qr_attendance_bp)
app.register_blueprint(system_bp)
app.register_blueprint(annual_report_bp)
app.register_blueprint(help_bp)
app.register_blueprint(public_bp)
app.register_blueprint(admissions_bp)
app.register_blueprint(public_content_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(admin_payments_bp)
app.register_blueprint(staff_att_bp)
app.register_blueprint(leave_bp)
app.register_blueprint(discounts_bp)
app.register_blueprint(visitors_bp)
app.register_blueprint(advances_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(online_exams_bp)
app.register_blueprint(automation_bp)
app.register_blueprint(hall_tickets_bp)
app.register_blueprint(photos_bp)
app.register_blueprint(report_cards_bp)
app.register_blueprint(password_reset_bp)


# ============================================================
# DIRECT ROUTES
# ============================================================
@app.route("/")
def home():
    """Homepage — gradient landing with login links"""
    return render_template("home.html")


@app.route("/health")
def health_check():
    """Health check — for uptime monitoring"""
    from database import get_conn
    status = {
        "status": "ok",
        "app": "School Management",
        "timestamp": datetime.now().isoformat(),
    }
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        status["database"] = "ok"
    except Exception as e:
        status["database"] = "error"
        status["db_error"] = str(e)[:100]
        return jsonify(status), 503
    return jsonify(status), 200


@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard"""
    from database import (
        count_students, total_collected, today_attendance_percent,
        count_unread_notices, get_fees_monthly_trend,
        get_attendance_trend, get_students_by_class,
        count_new_enquiries, count_active_staff, count_homework_this_week,
        get_computed_alerts, get_custom_alerts,
        get_upcoming_events, count_upcoming_events,
        get_today_snapshot, get_month_fee_progress,
        get_birthdays_today, get_recent_activity,
        get_top_performers, get_class_attendance_today,
        get_staff_attendance_today_summary_dashboard as get_staff_attendance_today_summary,
        count_transport_students,
        get_visitors_summary_dashboard as get_visitors_summary,
        get_pending_leave_count,
        get_total_advance_outstanding,
    )

    today_str = datetime.now().strftime("%Y-%m-%d")

    def safe(fn, default=None, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
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
    """Saare notifications dikhane ke liye page"""
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
                "severity": "high" if c.get("type") == "danger" else "medium"
            })
        for c in custom:
            all_notifs.append({
                "title": c.get("title", "Custom Alert"),
                "message": c.get("message", ""),
                "type": "info",
                "icon": "📢",
                "link": "#",
                "severity": "low"
            })
    except Exception as e:
        print("Error loading notifications:", e)
        all_notifs = []
        
    notif_data = {"items": all_notifs, "total": len(all_notifs)}
    return render_template("notifications.html", notifications=notif_data)


@app.route("/notifications/count")
@login_required
def notifications_count_api():
    """Bell icon par number dikhane ke liye API"""
    from database import get_computed_alerts, get_custom_alerts
    try:
        computed = get_computed_alerts() or []
        custom = get_custom_alerts(active_only=True) or []
        total = len(computed) + len(custom)
        urgent = sum(1 for n in computed if n.get('type') == 'danger')
        return jsonify({"count": total, "urgent": urgent})
    except Exception:
        return jsonify({"count": 0, "urgent": 0})


@app.route("/quick-search")
@login_required
def quick_search_api():
    """Phase 38 — Command palette global search"""
    try:
        from database import quick_search
        q = request.args.get("q", "").strip()
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
        "short_name": s.get("school_name", "School")[:12],
        "description": s.get("tagline", "School Management System"),
        "start_url": "/dashboard",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#f5f6fa",
        "theme_color": "#1e293b",
        "icons": [{"src": "/static/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
    }
    return jsonify(manifest)


@app.route("/sw.js")
def sw_route():
    resp = send_from_directory(app.static_folder, "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Content-Type"] = "application/javascript"
    return resp

@app.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        prompt = f"You are a helpful AI assistant for a School Management System. Keep your answers short, professional, and helpful. Query: {user_message}"
        
        # --- NAYA CODE YAHAN HAI ---
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        return jsonify({'reply': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/generate-exam', methods=['GET', 'POST'])
def generate_exam():
    if request.method == 'POST':
        subject = request.form.get('subject')
        grade = request.form.get('grade')
        
        prompt = f"""
        Create a school exam question paper for Class {grade}, Subject: {subject}.
        Format it beautifully using HTML tags like <h4>, <ol>, <li>. 
        Do NOT use markdown like ```html. Just return the raw HTML.
        Sections:
        - Section A: 5 MCQs (1 mark each)
        - Section B: 3 Short Questions (5 marks each)
        - Section C: 2 Long Questions (10 marks each)
        """
        try:
            # --- NAYA CODE YAHAN HAI ---
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            clean_html = response.text.replace('```html', '').replace('```', '').strip()
            return render_template('exam_paper_result.html', exam_content=clean_html, subject=subject, grade=grade)
        except Exception as e:
            return f"Error: {e}"
            
    return render_template('generate_exam_form.html')

# ============================================================
# CONTEXT PROCESSORS
# ============================================================
@app.context_processor
def inject_school():
    from database import get_settings
    try:
        return {"school": get_settings()}
    except Exception:
        return {"school": {"school_name": "School Management"}}

@app.context_processor
def inject_alert_count():
    if "admin_id" not in session:
        return {"alert_count": 0}
    try:
        from database import get_computed_alerts
        return {"alert_count": len(get_computed_alerts())}
    except Exception:
        return {"alert_count": 0}

@app.context_processor
def inject_chat_unread():
    if "admin_id" not in session:
        return {"chat_unread": 0}
    try:
        from database import count_unread_threads_for_admin
        return {"chat_unread": count_unread_threads_for_admin()}
    except Exception:
        return {"chat_unread": 0}

@app.context_processor
def inject_help_context():
    if "admin_id" not in session:
        return {"help_topic": None, "help_slug": None}
    slug = get_help_slug(request.path)
    topic = HELP_TOPICS.get(slug) if slug else None
    return {"help_topic": topic, "help_slug": slug}


# ============================================================
# ERROR HANDLERS
# ============================================================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith(("/api", "/qr-attendance/mark", "/qr-attendance/summary", "/quick-search")):
        return jsonify({"error": "not found"}), 404
    return render_template("errors/404.html"), 404

@app.errorhandler(403)
def forbidden(e):
    if request.path.startswith(("/api", "/qr-attendance")):
        return jsonify({"error": "forbidden"}), 403
    return render_template("errors/403.html"), 403

@app.errorhandler(500)
def server_error(e):
    import traceback
    traceback.print_exc()
    return render_template("errors/500.html"), 500

@app.errorhandler(Exception)
def catch_all(e):
    if isinstance(e, HTTPException):
        return e
    import traceback
    traceback.print_exc()
    return render_template("errors/500.html"), 500


# ============================================================
# BEFORE REQUEST — Rate Limiting
# ============================================================
from collections import defaultdict
from time import time as _time

_rate_store = defaultdict(list)

def _rate_limit_check(ip, endpoint, max_per_minute=60):
    now = _time()
    key = f"{ip}:{endpoint}"
    _rate_store[key] = [t for t in _rate_store[key] if now - t < 60]
    if len(_rate_store[key]) >= max_per_minute:
        return False
    _rate_store[key].append(now)
    return True

@app.before_request
def rate_limit_guard():
    sensitive = ["/qr-attendance/mark", "/login", "/parent/login", "/teacher/login", "/reset/"]
    path = request.path
    if any(path.startswith(p) for p in sensitive):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
        ip = ip.split(",")[0].strip()
        max_per_min = 300 if "qr-attendance" in path else 20
        if not _rate_limit_check(ip, path, max_per_min):
            return jsonify({"error": "Too many requests — thodi der baad try karo"}), 429


# ============================================================
# AFTER REQUEST — Security, Cache, Audit
# ============================================================
@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.after_request
def cache_static(response):
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800"
    elif request.path in ["/sw.js", "/manifest.json"]:
        response.headers["Cache-Control"] = "no-cache"
    return response


_AUDIT_EXCLUDE = ["/login", "/teacher/", "/parent/", "/site", "/reset/", "/alerts/log-send", "/pay/", "/automation/cron"]

@app.after_request
def auto_audit(response):
    try:
        if "admin_id" not in session:
            return response
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return response
        path = request.path
        if any(path.startswith(p) for p in _AUDIT_EXCLUDE):
            return response
        if 200 <= response.status_code < 400:
            entity = None
            entity_map = {
                "/students/": "student", "/classes/": "classes", "/fees/": "fees", "/staff/": "staff",
                "/exams/": "exams", "/salary/": "salary", "/admin-users/": "admin_users",
                "/notices/": "notices", "/events/": "events", "/library/": "library",
                "/hostel/": "hostel", "/transport/": "transport", "/visitors/": "visitors",
                "/advances/": "advances", "/leave/": "leave", "/automation/": "automation",
            }
            for prefix, ent in entity_map.items():
                if path.startswith(prefix):
                    entity = ent
                    break
            from database import log_audit
            
            # Aakhri code jo cut gaya tha, use complete kiya hai
            log_audit(
                session["admin_id"],
                session.get("admin_username", "?"),
                action=f"{request.method} {path}",
                entity_type=entity,
                details=f"Path: {path}"
            )
    except Exception as e:
        print(f"Audit Error: {e}")
    return response
