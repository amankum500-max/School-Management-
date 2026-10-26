from datetime import datetime
from flask import (
    Blueprint, render_template, request, abort
)
from modules.auth import login_required
from database import get_student, get_students_full, get_settings, get_classes_list

id_card_bp = Blueprint("id_card", __name__, url_prefix="/students/id-cards")

def _academic_year():
    """April se March tak academic year"""
    now = datetime.now()
    y = now.year
    if now.month >= 4:
        return f"{y}-{str(y+1)[-2:]}"
    return f"{y-1}-{str(y)[-2:]}"

@id_card_bp.route("/<int:student_id>")
@login_required
def single(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))
    return render_template(
        "students/id_card.html",
        students=[student],
        school=get_settings(),
        bulk=False,
        ay=_academic_year()
    )

@id_card_bp.route("/bulk")
@login_required
def bulk():
    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    students = []
    if class_name:
        students = get_students_full(class_name, section or None)

    return render_template(
        "students/id_card.html",
        students=students,
        school=get_settings(),
        bulk=True,
        classes=get_classes_list(),
        selected_class=class_name,
        selected_section=section,
        ay=_academic_year()
    )
