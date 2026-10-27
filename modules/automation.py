import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, session
)
from modules.auth import login_required, role_required
from database import (
    get_automation_settings, update_automation_settings,
    get_sms_quota_remaining, start_automation_run,
    complete_automation_run, update_last_run, get_automation_runs,
    get_fee_defaulters_for_sms, get_absentees_today_for_sms,
    get_library_overdue_for_sms, get_upcoming_events_for_sms,
    get_students_with_low_attendance_for_sms,
    was_sms_sent_to_student_today, log_sms, get_sms_template
)
import sms_service

automation_bp = Blueprint("automation", __name__, url_prefix="/automation")

TASK_TYPES = {
    "fee": {"label": "Fee Reminders", "icon": "💰", "template_cat": "fee"},
    "absent": {"label": "Absent Alerts", "icon": "❌", "template_cat": "attendance"},
    "library": {"label": "Library Overdue", "icon": "📚", "template_cat": "custom"},
    "event": {"label": "Event Reminders", "icon": "📅", "template_cat": "notice"},
    "attendance": {"label": "Low Attendance", "icon": "📊", "template_cat": "attendance"},
}


# ---------- Admin UI ----------
@automation_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    settings = get_automation_settings()
    quota = get_sms_quota_remaining()
    runs = get_automation_runs(limit=20)
    return render_template("automation/index.html",
                           settings=settings, quota=quota, runs=runs,
                           task_types=TASK_TYPES,
                           configured=sms_service.is_configured())


@automation_bp.route("/save-settings", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def save_settings():
    update_automation_settings(request.form.to_dict())
    flash("Automation settings saved", "success")
    return redirect(url_for("automation.index"))


@automation_bp.route("/trigger/<task_type>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def trigger(task_type):
    """Manual trigger for testing"""
    if task_type not in TASK_TYPES:
        flash("Invalid task type", "error")
        return redirect(url_for("automation.index"))

    result = run_task(task_type, trigger_type="manual")
    if result["status"] == "completed":
        flash(f"{result['sent']} SMS sent, {result['skipped']} skipped, "
              f"{result['failed']} failed", "success")
    else:
        flash(f"Task {result['status']}: {result.get('error', '')}", "error")
    return redirect(url_for("automation.index"))


@automation_bp.route("/preview/<task_type>")
@login_required
@role_required("super_admin", "admin")
def preview(task_type):
    """See who will receive SMS without sending"""
    if task_type not in TASK_TYPES:
        return jsonify({"error": "Invalid task"}), 400

    recipients = get_recipients_for_task(task_type)
    return jsonify({
        "count": len(recipients),
        "recipients": recipients[:50]  # first 50
    })


# ---------- Cron endpoints (called from GitHub Actions) ----------
def _check_cron_auth():
    """Bearer token validation for cron endpoints"""
    expected = os.getenv("AUTOMATION_SECRET", "")
    if not expected:
        return False
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {expected}"


@automation_bp.route("/cron/<task_type>", methods=["POST", "GET"])
def cron_run(task_type):
    """External cron hits this endpoint"""
    if not _check_cron_auth():
        return jsonify({"error": "Unauthorized"}), 401

    if task_type not in TASK_TYPES:
        return jsonify({"error": "Invalid task"}), 400

    # Check if task is enabled in settings
    settings = get_automation_settings()
    enabled_key = f"{task_type}_enabled" if task_type != "attendance" \
                  else "low_attendance_enabled"
    if task_type == "fee":
        enabled = settings["fee_reminders"]
    elif task_type == "absent":
        enabled = settings["absent_alerts"]
    elif task_type == "library":
        enabled = settings["library_overdue"]
    elif task_type == "event":
        enabled = settings["event_reminders"]
    elif task_type == "attendance":
        enabled = settings["low_attendance"]
    else:
        enabled = False

    if not enabled:
        return jsonify({"status": "skipped", "reason": "Disabled in settings"})

    result = run_task(task_type, trigger_type="cron")
    return jsonify(result)


# ---------- Task Runners ----------
def get_recipients_for_task(task_type):
    """Return list of recipient dicts without sending"""
    if task_type == "fee":
        return get_fee_defaulters_for_sms()
    elif task_type == "absent":
        return get_absentees_today_for_sms()
    elif task_type == "library":
        return get_library_overdue_for_sms()
    elif task_type == "event":
        return get_upcoming_events_for_sms(days_ahead=2)
    elif task_type == "attendance":
        return get_students_with_low_attendance_for_sms()
    return []


def get_template_for_task(task_type):
    """Find appropriate SMS template by category"""
    from database import get_sms_templates
    cat = TASK_TYPES[task_type]["template_cat"]
    templates = get_sms_templates(active_only=True)
    for t in templates:
        if t["category"] == cat:
            return t
    return templates[0] if templates else None


def run_task(task_type, trigger_type="manual"):
    """Main task runner"""
    run_id = start_automation_run(task_type, trigger_type=trigger_type)

    # Check SMS quota
    quota = get_sms_quota_remaining()
    if quota["remaining"] <= 0:
        complete_automation_run(run_id, "skipped",
                                error="Daily SMS quota exceeded")
        return {"status": "skipped", "reason": "Daily SMS quota exceeded"}

    # Check provider configured
    if not sms_service.is_configured():
        complete_automation_run(run_id, "failed",
                                error="SMS provider not configured")
        return {"status": "failed", "error": "SMS provider not configured"}

    template = get_template_for_task(task_type)
    if not template:
        complete_automation_run(run_id, "failed",
                                error="No SMS template found")
        return {"status": "failed", "error": "No SMS template found"}

    recipients = get_recipients_for_task(task_type)
    if not recipients:
        complete_automation_run(run_id, "completed", total=0)
        update_last_run(task_type)
        return {"status": "completed", "sent": 0, "skipped": 0, "failed": 0}

    from database import get_settings
    school = get_settings()
    school_name = school.get("school_name", "School")

    sent = 0
    failed = 0
    skipped = 0
    quota_exceeded = False

    for r in recipients:
        # Quota check per message
        current_quota = get_sms_quota_remaining()
        if current_quota["remaining"] <= 0:
            quota_exceeded = True
            skipped += (len(recipients) - sent - failed - skipped)
            break

        # Get student_id (from events it's None)
        student_id = r.get("id") if task_type != "event" else None

        # Spam guard — same student same day
        if student_id and was_sms_sent_to_student_today(student_id):
            skipped += 1
            continue

        # Build variables
        class_str = f"{r.get('class_name') or ''}{('-' + r['section']) if r.get('section') else ''}"
        variables = {
            "name": r.get("name", ""),
            "parent": r.get("parent_name", "Parent"),
            "class": class_str,
            "school": school_name,
            "amount": f"{r.get('pending', 0):.0f}",
            "month": r.get("month", ""),
            "date": r.get("start_date", "").strftime("%d %b") if r.get("start_date") else "",
            "receipt": "",
            "exam": "",
            "book": r.get("book_title", ""),
            "event": r.get("title", ""),
        }

        # Compose message from template body
        body = sms_service._render_body(template["body"], variables)
        phone = r.get("phone", "")

        # For events — no per-student list, skip for now
        if task_type == "event":
            # Just log an event notification for admin
            skipped += 1
            continue

        res = sms_service.send_sms(
            phone, body,
            template_id=template.get("msg91_template_id"),
            variables=variables
        )

        log_sms(
            student_id, phone, res.get("rendered_body", body),
            template["id"], res.get("provider", "?"),
            res.get("message_id", ""),
            "sent" if res["ok"] else "failed",
            res.get("error", ""), None
        )
        if res["ok"]:
            sent += 1
        else:
            failed += 1

    total = len(recipients)
    final_status = "completed" if not quota_exceeded else "completed"

    complete_automation_run(run_id, final_status,
                            total=total, sent=sent, failed=failed,
                            skipped=skipped,
                            error="Quota hit mid-run" if quota_exceeded else None)
    update_last_run(task_type)

    return {"status": final_status, "sent": sent,
            "failed": failed, "skipped": skipped, "total": total}
