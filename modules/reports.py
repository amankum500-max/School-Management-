import io
import csv
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, Response, abort
)
from modules.auth import login_required
from database import (
    get_fee_report, get_fee_report_summary,
    get_attendance_report, get_defaulters,
    get_classes_list
)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

def _default_range():
    """Aaj se 30 din pehle tak"""
    today = datetime.now().date()
    start = today - timedelta(days=30)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

@reports_bp.route("/")
@login_required
def index():
    return render_template("reports/index.html")

# ---------- Fee Report ----------
@reports_bp.route("/fees")
@login_required
def fees():
    start, end = _default_range()
    start = request.args.get("start", start)
    end = request.args.get("end", end)
    class_name = request.args.get("class", "").strip()

    rows = get_fee_report(start, end, class_name or None)
    summary = get_fee_report_summary(start, end, class_name or None)

    return render_template(
        "reports/fees.html",
        payments=rows, summary=summary,
        start=start, end=end,
        classes=get_classes_list(),
        selected_class=class_name
    )

@reports_bp.route("/fees/export")
@login_required
def fees_export():
    start, end = _default_range()
    start = request.args.get("start", start)
    end = request.args.get("end", end)
    class_name = request.args.get("class", "").strip()

    rows = get_fee_report(start, end, class_name or None)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Receipt No", "Paid At", "Month", "Fee Type",
        "Amount", "Mode", "Student", "Roll", "Class", "Section"
    ])
    for r in rows:
        writer.writerow([
            r["receipt_no"], r["paid_at"].strftime("%Y-%m-%d %H:%M") if r["paid_at"] else "",
            r["month"], r["fee_type"], r["amount"], r["mode"],
            r["student_name"], r["roll"] or "",
            r["class_name"] or "", r["section"] or ""
        ])

    filename = f"fees_{start}_to_{end}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ---------- Attendance Report ----------
@reports_bp.route("/attendance")
@login_required
def attendance():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    class_name = request.args.get("class", "").strip()

    rows = get_attendance_report(month, class_name or None)

    total_students = len(rows)
    below_75 = sum(1 for r in rows if r["percent"] < 75 and r["total"] > 0)

    return render_template(
        "reports/attendance.html",
        rows=rows, month=month,
        classes=get_classes_list(),
        selected_class=class_name,
        total_students=total_students,
        below_75=below_75
    )

@reports_bp.route("/attendance/export")
@login_required
def attendance_export():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    class_name = request.args.get("class", "").strip()
    rows = get_attendance_report(month, class_name or None)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Student", "Roll", "Class", "Section",
        "Present", "Absent", "Late", "Leave", "Total", "Percent"
    ])
    for r in rows:
        writer.writerow([
            r["name"], r["roll"] or "", r["class_name"] or "",
            r["section"] or "", r["present"], r["absent"],
            r["late"], r["leave"], r["total"], r["percent"]
        ])

    filename = f"attendance_{month}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ---------- Defaulter Report ----------
@reports_bp.route("/defaulters")
@login_required
def defaulters():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    rows = get_defaulters(month)
    return render_template(
        "reports/defaulters.html",
        month=month,
        rows=[
            {"id": r[0], "name": r[1], "roll": r[2], "class_name": r[3],
             "section": r[4], "phone": r[5],
             "due": float(r[6]), "paid": float(r[7]),
             "pending": float(r[6]) - float(r[7])}
            for r in rows
        ],
        total_pending=sum(float(r[6]) - float(r[7]) for r in rows)
    )

@reports_bp.route("/defaulters/export")
@login_required
def defaulters_export():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    rows = get_defaulters(month)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Student", "Roll", "Class", "Section", "Parent Phone",
        "Due", "Paid", "Pending"
    ])
    for r in rows:
        writer.writerow([
            r[1], r[2] or "", r[3] or "", r[4] or "",
            r[5] or "", float(r[6]), float(r[7]),
            float(r[6]) - float(r[7])
        ])

    filename = f"defaulters_{month}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
