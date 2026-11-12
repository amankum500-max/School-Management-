"""
Year Report Card Module — Complete Routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from functools import wraps
import database as db
from datetime import datetime, date

# 👇 यहाँ वेरिएबल का नाम report_cards_bp कर दिया गया है ताकि app.py से मैच हो जाए
report_cards_bp = Blueprint('report_cards', __name__, url_prefix='/report-cards')

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_id'):
            flash("Please login first", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────
# 1. INDEX — Select student & academic year
# ─────────────────────────────────────────────────────────
@report_cards_bp.route('/')
@login_required
def index():
    class_name = request.args.get('class_name', '')
    students = db.get_students_full(class_name=class_name or None)
    classes = db.get_classes_list()
    years = db.get_academic_year_options()
    return render_template('report_card/index.html',
                           students=students, classes=classes,
                           years=years, selected_class=class_name,
                           current_year=db.get_current_academic_year())


# ─────────────────────────────────────────────────────────
# 2. VIEW YEAR REPORT (single student)
# ─────────────────────────────────────────────────────────
@report_cards_bp.route('/view/<int:student_id>')
@login_required
def view(student_id):
    academic_year = request.args.get('year') or db.get_current_academic_year()
    report = db.get_student_year_report(student_id, academic_year)
    if not report:
        flash("Report data not found for this student/year", "danger")
        return redirect(url_for('report_cards.index'))

    settings = db.get_settings()
    years = db.get_academic_year_options()
    return render_template('report_card/view.html',
                           report=report, settings=settings,
                           selected_year=academic_year, years=years)


# ─────────────────────────────────────────────────────────
# 3. PRINT VIEW (clean print layout)
# ─────────────────────────────────────────────────────────
@report_cards_bp.route('/print/<int:student_id>')
@login_required
def print_view(student_id):
    academic_year = request.args.get('year') or db.get_current_academic_year()
    report = db.get_student_year_report(student_id, academic_year)
    if not report:
        abort(404)
    settings = db.get_settings()
    return render_template('report_card/print.html',
                           report=report, settings=settings)


# ─────────────────────────────────────────────────────────
# 4. SAVE REMARKS
# ─────────────────────────────────────────────────────────
@report_cards_bp.route('/remarks/<int:student_id>', methods=['POST'])
@login_required
def save_remarks(student_id):
    academic_year = request.form.get('academic_year') or db.get_current_academic_year()
    teacher_remark = request.form.get('teacher_remark', '').strip()
    principal_remark = request.form.get('principal_remark', '').strip()
    conduct = request.form.get('conduct', 'Good').strip()

    ok = db.save_report_card_remarks(
        student_id=student_id,
        teacher_remark=teacher_remark,
        principal_remark=principal_remark,
        conduct=conduct,
        academic_year=academic_year
    )
    if ok:
        flash("Remarks saved successfully", "success")
    else:
        flash("Failed to save remarks", "danger")
    return redirect(url_for('report_cards.view',
                            student_id=student_id, year=academic_year))


# ─────────────────────────────────────────────────────────
# 5. CLASS SUMMARY (all students of a class)
# ─────────────────────────────────────────────────────────
@report_cards_bp.route('/class-summary')
@login_required
def class_summary():
    class_name = request.args.get('class_name', '')
    academic_year = request.args.get('year') or db.get_current_academic_year()
    classes = db.get_classes_list()
    years = db.get_academic_year_options()

    summary = []
    if class_name:
        summary = db.get_class_report_card_summary(class_name, academic_year)
        # rank
        sorted_rows = sorted(summary, key=lambda r: r["percentage"], reverse=True)
        for i, r in enumerate(sorted_rows):
            r["rank"] = i + 1
        summary = sorted_rows

    return render_template('report_card/class_summary.html',
                           summary=summary, classes=classes, years=years,
                           selected_class=class_name,
                           selected_year=academic_year)


# ─────────────────────────────────────────────────────────
# 6. BULK PRINT CLASS (for parent-teacher meeting)
# ─────────────────────────────────────────────────────────
@report_cards_bp.route('/bulk/<class_name>')
@login_required
def bulk_print(class_name):
    academic_year = request.args.get('year') or db.get_current_academic_year()
    students = db.get_students_full(class_name=class_name)
    settings = db.get_settings()

    reports = []
    for s in students:
        try:
            r = db.get_student_year_report(s["id"], academic_year)
            if r:
                reports.append(r)
        except Exception:
            continue

    return render_template('report_card/bulk.html',
                           reports=reports, class_name=class_name,
                           academic_year=academic_year, settings=settings)
