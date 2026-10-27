from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    get_student_year_report, save_report_card_remarks,
    get_class_report_card_summary, get_current_academic_year,
    get_academic_year_options, get_student, get_classes_list,
    get_children_for_parent
)

report_cards_bp = Blueprint("report_cards", __name__,
                            url_prefix="/report-cards")

CONDUCT_OPTIONS = ["Excellent", "Good", "Satisfactory", "Needs Improvement"]


@report_cards_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    class_name = request.args.get("class", "").strip()
    ay = request.args.get("ay") or get_current_academic_year()

    summary = []
    if class_name:
        summary = get_class_report_card_summary(class_name, ay)

    return render_template("report_cards/index.html",
                           classes=get_classes_list(),
                           selected_class=class_name,
                           academic_year=ay,
                           ay_options=get_academic_year_options(),
                           summary=summary)


@report_cards_bp.route("/view/<int:student_id>")
@login_required
@role_required("super_admin", "admin")
def view(student_id):
    ay = request.args.get("ay") or get_current_academic_year()
    report = get_student_year_report(student_id, ay)
    if not report:
        flash("Report card data nahi mila. Exam marks check karo.", "error")
        return redirect(url_for("report_cards.index"))

    return render_template("report_cards/view.html",
                           r=report,
                           conduct_options=CONDUCT_OPTIONS,
                           ay_options=get_academic_year_options())


@report_cards_bp.route("/print/<int:student_id>")
@login_required
@role_required("super_admin", "admin")
def print_view(student_id):
    ay = request.args.get("ay") or get_current_academic_year()
    report = get_student_year_report(student_id, ay)
    if not report:
        abort(404)
    return render_template("report_cards/print.html", r=report)


@report_cards_bp.route("/save-remarks/<int:student_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def save_remarks(student_id):
    ay = request.form.get("academic_year") or get_current_academic_year()
    teacher_remark = request.form.get("teacher_remark", "").strip()
    principal_remark = request.form.get("principal_remark", "").strip()
    conduct = request.form.get("conduct", "Good")

    save_report_card_remarks(
        student_id, ay, teacher_remark, principal_remark,
        conduct, session["admin_id"]
    )
    flash("Remarks save ho gaye", "success")
    return redirect(url_for("report_cards.view", student_id=student_id, ay=ay))


@report_cards_bp.route("/bulk-print")
@login_required
@role_required("super_admin", "admin")
def bulk_print():
    """Class ke saare students ke report cards ek page pe"""
    class_name = request.args.get("class", "").strip()
    ay = request.args.get("ay") or get_current_academic_year()

    if not class_name:
        flash("Class select karo", "error")
        return redirect(url_for("report_cards.index"))

    summary = get_class_report_card_summary(class_name, ay)
    reports = []
    for s in summary:
        r = get_student_year_report(s["student_id"], ay)
        if r:
            reports.append(r)

    return render_template("report_cards/bulk_print.html",
                           reports=reports, ay=ay,
                           class_name=class_name)
