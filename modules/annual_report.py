from datetime import date
from flask import Blueprint, render_template, request
from modules.auth import login_required, role_required
from database import (
    get_annual_financial_summary, get_annual_student_summary,
    get_annual_academic_summary, get_annual_attendance_summary,
    get_annual_fee_defaulters_summary
)

annual_report_bp = Blueprint("annual_report", __name__,
                             url_prefix="/reports/annual")

def _current_fy():
    """Current financial year (Apr-Mar)"""
    today = date.today()
    if today.month >= 4:
        return today.year
    return today.year - 1

@annual_report_bp.route("/")
@login_required
@role_required("super_admin", "admin", "accountant")
def index():
    fy = request.args.get("fy", type=int) or _current_fy()
    if fy < 2020 or fy > date.today().year + 1:
        fy = _current_fy()

    financial = get_annual_financial_summary(fy)
    students = get_annual_student_summary(fy)
    academic = get_annual_academic_summary(fy)
    attendance = get_annual_attendance_summary(fy)
    fee_eff = get_annual_fee_defaulters_summary(fy)

    # Year options — last 5 years
    current = _current_fy()
    fy_options = list(range(current, current - 5, -1))

    return render_template(
        "annual_report/index.html",
        fy=fy, fy_label=financial["fy_label"],
        fy_options=fy_options,
        financial=financial, students=students,
        academic=academic, attendance=attendance,
        fee_eff=fee_eff
    )

@annual_report_bp.route("/print")
@login_required
@role_required("super_admin", "admin", "accountant")
def print_view():
    fy = request.args.get("fy", type=int) or _current_fy()
    financial = get_annual_financial_summary(fy)
    students = get_annual_student_summary(fy)
    academic = get_annual_academic_summary(fy)
    attendance = get_annual_attendance_summary(fy)
    fee_eff = get_annual_fee_defaulters_summary(fy)

    return render_template(
        "annual_report/print.html",
        fy=fy, fy_label=financial["fy_label"],
        financial=financial, students=students,
        academic=academic, attendance=attendance,
        fee_eff=fee_eff
    )
