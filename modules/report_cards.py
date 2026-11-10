from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort, jsonify
)
import os
from google import genai
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

# Gemini AI Client
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


# ---------------------------------------------------------------------------
# Helpers (validation)
# ---------------------------------------------------------------------------
def _safe_academic_year(raw_ay):
    ay = (raw_ay or "").strip()
    allowed = get_academic_year_options() or []
    if ay and ay in allowed:
        return ay
    return get_current_academic_year()


def _safe_class(raw_class):
    class_name = (raw_class or "").strip()
    if not class_name:
        return ""
    allowed = get_classes_list() or []
    if class_name in allowed:
        return class_name
    return ""


def _safe_conduct(raw_conduct):
    conduct = (raw_conduct or "").strip()
    if conduct in CONDUCT_OPTIONS:
        return conduct
    return "Good"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@report_cards_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    class_name = _safe_class(request.args.get("class"))
    ay = _safe_academic_year(request.args.get("ay"))

    summary = []
    if class_name:
        try:
            # Database se data fetch karein
            db_summary = get_class_report_card_summary(class_name, ay)
            
            # 🚨 FIX: Agar database se None aaye, toh usko empty list [] banayein
            if db_summary is not None:
                summary = db_summary
            else:
                summary = []
                
        except Exception as e:
            # 🚨 FIX: Agar database error aaye toh app crash na ho
            print(f"Database Error in Report Card Index: {e}")
            flash("Database se data fetch karne mein error aaya. Pehle marks enter karein.", "error")
            summary = []

    return render_template(
        "report_cards/index.html",
        classes=get_classes_list(),
        selected_class=class_name,
        academic_year=ay,
        ay_options=get_academic_year_options(),
        summary=summary,
    )


@report_cards_bp.route("/view/<int:student_id>")
@login_required
@role_required("super_admin", "admin")
def view(student_id):
    ay = _safe_academic_year(request.args.get("ay"))

    try:
        report = get_student_year_report(student_id, ay)
    except Exception as e:
        flash(f"Report card load karte waqt error: {e}", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    if not report:
        flash("Report card data nahi mila. Exam marks check karo.", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    # CHART FIX: Ensure all_subjects and subject_averages exist for view.html
    if 'subject_averages' not in report:
        report['subject_averages'] = {}
    if 'all_subjects' not in report:
        report['all_subjects'] = list(report['subject_averages'].keys())

    return render_template(
        "report_cards/view.html",
        r=report,
        conduct_options=CONDUCT_OPTIONS,
        ay_options=get_academic_year_options(),
        selected_ay=ay,
    )


@report_cards_bp.route("/print/<int:student_id>")
@login_required
@role_required("super_admin", "admin")
def print_view(student_id):
    ay = _safe_academic_year(request.args.get("ay"))

    try:
        report = get_student_year_report(student_id, ay)
    except Exception as e:
        flash(f"Print view load error: {e}", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    if not report:
        flash("Report card data nahi mila. Exam marks check karo.", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    return render_template("report_cards/print.html", r=report)


@report_cards_bp.route("/save-remarks/<int:student_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def save_remarks(student_id):
    ay = _safe_academic_year(request.form.get("academic_year"))
    teacher_remark = (request.form.get("teacher_remark") or "").strip()
    principal_remark = (request.form.get("principal_remark") or "").strip()
    conduct = _safe_conduct(request.form.get("conduct"))

    try:
        student = get_student(student_id)
    except Exception as e:
        flash(f"Student load error: {e}", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    if not student:
        flash("Student nahi mila", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    try:
        save_report_card_remarks(
            student_id, ay, teacher_remark, principal_remark,
            conduct, session["admin_id"],
        )
    except Exception as e:
        flash(f"Remarks save nahi ho paye: {e}", "error")
        return redirect(url_for("report_cards.view", student_id=student_id, ay=ay))

    flash("Remarks save ho gaye", "success")
    return redirect(url_for("report_cards.view", student_id=student_id, ay=ay))


@report_cards_bp.route("/bulk-print")
@login_required
@role_required("super_admin", "admin")
def bulk_print():
    class_name = _safe_class(request.args.get("class"))
    ay = _safe_academic_year(request.args.get("ay"))

    if not class_name:
        flash("Class select karo", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    try:
        summary = get_class_report_card_summary(class_name, ay)
        if summary is None:
            summary = []
    except Exception as e:
        flash(f"Class summary load error: {e}", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    reports = []
    try:
        from database import get_students_year_reports_bulk
        student_ids = [s["student_id"] for s in summary]
        reports = get_students_year_reports_bulk(student_ids, ay) or []
    except ImportError:
        for s in summary:
            try:
                r = get_student_year_report(s["student_id"], ay)
            except Exception:
                r = None
            if r:
                reports.append(r)
    except Exception as e:
        flash(f"Bulk report load error: {e}", "error")
        return redirect(url_for("report_cards.index", ay=ay))

    return render_template(
        "report_cards/bulk_print.html",
        reports=reports,
        ay=ay,
        class_name=class_name,
    )

# ---------------------------------------------------------------------------
# 🤖 AI GENERATION API ROUTE
# ---------------------------------------------------------------------------
@report_cards_bp.route("/api/generate-ai", methods=["POST"])
@login_required
def generate_ai_remark():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
        
    student_name = data.get("name", "Student")
    marks_data = data.get("marks", {})

    if not marks_data:
        return jsonify({"error": "No marks data provided for AI"}), 400

    prompt = f"""
    You are an experienced school teacher. Write a short, professional, and encouraging 
    year-end report card remark (3-4 sentences) for a student named {student_name}.
    
    Here are their subject averages: {marks_data}
    
    Instructions:
    1. Highlight their best subject.
    2. Gently suggest improvement in their weakest subject.
    3. Keep the tone positive and motivating.
    4. Do not use any HTML tags or markdown formatting, just plain text.
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return jsonify({"remark": response.text.strip()})
    except Exception as e:
        print(f"Gemini AI Error: {e}")
        return jsonify({"error": "Failed to generate AI remark"}), 500
