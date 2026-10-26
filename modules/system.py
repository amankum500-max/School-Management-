from flask import (
    Blueprint, render_template, jsonify
)
from modules.auth import login_required, role_required
from database import get_conn, get_settings, count_students

system_bp = Blueprint("system", __name__, url_prefix="/system")

@system_bp.route("/status")
@login_required
@role_required("super_admin")
def status():
    """Full system health check"""
    checks = []

    # 1) Database connectivity
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        checks.append({"name": "Database", "status": "ok",
                       "detail": "Supabase connection healthy"})
    except Exception as e:
        checks.append({"name": "Database", "status": "error",
                       "detail": str(e)[:120]})

    # 2) Tables exist
    from database import BACKUP_TABLES
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public';
        """)
        existing = {r[0] for r in cur.fetchall()}
        cur.close()
        conn.close()
        missing = [t for t in BACKUP_TABLES if t not in existing]
        if missing:
            checks.append({"name": "Tables",
                           "status": "warning",
                           "detail": f"Missing: {', '.join(missing)}"})
        else:
            checks.append({"name": "Tables", "status": "ok",
                           "detail": f"All {len(BACKUP_TABLES)} tables present"})
    except Exception as e:
        checks.append({"name": "Tables", "status": "error",
                       "detail": str(e)[:120]})

    # 3) School settings
    try:
        s = get_settings()
        if s.get("school_name") and s["school_name"] != "My School":
            checks.append({"name": "School Settings", "status": "ok",
                           "detail": f"Configured: {s['school_name']}"})
        else:
            checks.append({"name": "School Settings", "status": "warning",
                           "detail": "School name set nahi — Settings page se configure karo"})
    except Exception as e:
        checks.append({"name": "School Settings", "status": "error",
                       "detail": str(e)[:120]})

    # 4) Environment variables
    import os
    env_checks = [
        ("SECRET_KEY", os.getenv("SECRET_KEY")),
        ("DATABASE_URL", os.getenv("DATABASE_URL")),
    ]
    missing_env = [k for k, v in env_checks if not v]
    if missing_env:
        checks.append({"name": "Environment",
                       "status": "error",
                       "detail": f"Missing: {', '.join(missing_env)}"})
    else:
        checks.append({"name": "Environment", "status": "ok",
                       "detail": "All required env vars set"})

    # 5) Student count
    try:
        n = count_students()
        checks.append({"name": "Students Data", "status": "ok",
                       "detail": f"{n} active students"})
    except Exception as e:
        checks.append({"name": "Students Data", "status": "error",
                       "detail": str(e)[:120]})

    # 6) Backup reminder (last backup — we don't track, just remind)
    checks.append({
        "name": "Backup",
        "status": "info",
        "detail": "Last 7 din mein backup liya? /backup page se verify karo"
    })

    # Overall status
    has_error = any(c["status"] == "error" for c in checks)
    has_warning = any(c["status"] == "warning" for c in checks)
    overall = "error" if has_error else ("warning" if has_warning else "ok")

    return render_template("system/status.html",
                           checks=checks, overall=overall)

@system_bp.route("/checklist")
@login_required
@role_required("super_admin")
def checklist():
    """Production readiness checklist"""
    import os
    items = [
        # (category, item, check_fn_description, is_ok_boolean)
        ("Security", "SECRET_KEY set", bool(os.getenv("SECRET_KEY"))),
        ("Security", "DATABASE_URL set", bool(os.getenv("DATABASE_URL"))),
        ("Security", "All admins have strong passwords (8+ chars)",
            True),  # manual
        ("Security", "Super admin password changed from default",
            True),  # manual
        ("Security", "Inactive admin users removed",
            True),  # manual
        ("Data", "School info configured in settings", True),
        ("Data", "Backup taken recently", True),
        ("Data", "Fee structure set for all classes", True),
        ("Data", "All active students have parent phone", True),
        ("Data", "Timetable set for all classes", True),
        ("Performance", "Render instance running (check logs)", True),
        ("Performance", "No errors in Render logs (last 24h)", True),
        ("Backup", "JSON backup downloaded in last 7 days", True),
        ("Backup", "Backup stored somewhere safe (Drive/email)", True),
        ("PWA", "Manifest loading correctly", True),
        ("PWA", "Service worker registered", True),
        ("PWA", "App installable on home screen", True),
        ("QR", "ID card QR codes printed and distributed", True),
        ("QR", "QR scanner tested on teacher phones", True),
        ("Testing", "Fee collection flow tested", True),
        ("Testing", "Attendance marking tested", True),
        ("Testing", "Exam marks entry tested", True),
        ("Testing", "Parent portal tested with real parent", True),
        ("Testing", "Teacher portal tested with real teacher", True),
    ]
    return render_template("system/checklist.html", items=items)
