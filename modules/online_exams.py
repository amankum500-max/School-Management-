from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    create_online_exam, get_online_exams, get_online_exam,
    update_online_exam, delete_online_exam, toggle_exam_publish,
    get_exam_questions, add_exam_question, delete_exam_question,
    get_exam_results, get_classes_list
)

online_exams_bp = Blueprint("online_exams", __name__,
                             url_prefix="/online-exams")


@online_exams_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    class_name = request.args.get("class", "").strip()
    exams = get_online_exams(class_name=class_name or None)
    return render_template("online_exams/index.html",
                           exams=exams,
                           classes=get_classes_list(),
                           selected_class=class_name)


@online_exams_bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("title") or not data.get("class_name"):
            flash("Title aur class zaroori hain", "error")
            return redirect(url_for("online_exams.add"))
        eid = create_online_exam(data, session["admin_id"])
        flash("Exam create ho gaya. Ab questions add karo.", "success")
        return redirect(url_for("online_exams.manage", eid=eid))
    return render_template("online_exams/form.html",
                           exam=None, mode="add",
                           classes=get_classes_list())


@online_exams_bp.route("/<int:eid>")
@login_required
@role_required("super_admin", "admin")
def manage(eid):
    exam = get_online_exam(eid)
    if not exam:
        abort(404)
    questions = get_exam_questions(eid)
    results = get_exam_results(eid) if exam["is_published"] else []
    return render_template("online_exams/manage.html",
                           exam=exam, questions=questions,
                           results=results)


@online_exams_bp.route("/<int:eid>/edit", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def edit(eid):
    exam = get_online_exam(eid)
    if not exam:
        abort(404)
    if request.method == "POST":
        update_online_exam(eid, request.form.to_dict())
        flash("Exam update ho gaya", "success")
        return redirect(url_for("online_exams.manage", eid=eid))
    return render_template("online_exams/form.html",
                           exam=exam, mode="edit",
                           classes=get_classes_list())


@online_exams_bp.route("/<int:eid>/delete", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def remove(eid):
    delete_online_exam(eid)
    flash("Exam delete ho gaya", "success")
    return redirect(url_for("online_exams.index"))


@online_exams_bp.route("/<int:eid>/toggle-publish", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def toggle_publish(eid):
    exam = get_online_exam(eid)
    if not exam:
        abort(404)
    # Need at least 1 question to publish
    if not exam["is_published"]:
        qs = get_exam_questions(eid)
        if not qs:
            flash("Publish karne se pehle koi question add karo", "error")
            return redirect(url_for("online_exams.manage", eid=eid))
    toggle_exam_publish(eid, not exam["is_published"])
    flash("Publish status updated", "success")
    return redirect(url_for("online_exams.manage", eid=eid))


@online_exams_bp.route("/<int:eid>/questions/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_question(eid):
    exam = get_online_exam(eid)
    if not exam:
        abort(404)
    data = request.form
    if not data.get("question_text") or not data.get("option_a") \
       or not data.get("option_b") or not data.get("correct_option"):
        flash("Question, A, B, aur correct option zaroori hain", "error")
        return redirect(url_for("online_exams.manage", eid=eid))

    try:
        add_exam_question(
            eid,
            data["question_text"],
            data["option_a"], data["option_b"],
            data.get("option_c", ""), data.get("option_d", ""),
            data["correct_option"],
            int(data.get("marks") or 1)
        )
        flash("Question add ho gaya", "success")
    except Exception as e:
        flash(f"Error: {str(e)[:100]}", "error")
    return redirect(url_for("online_exams.manage", eid=eid))


@online_exams_bp.route("/questions/<int:qid>/delete", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def remove_question(qid):
    eid = delete_exam_question(qid)
    if eid:
        flash("Question delete ho gaya", "success")
        return redirect(url_for("online_exams.manage", eid=eid))
    return redirect(url_for("online_exams.index"))
    # ... Aapka purana code upar rahega ...

# ==========================================
# NAYA CODE YAHAN SE SHURU HOTA HAI
# (Dhyan dein: @exams_bp ki jagah @online_exams_bp kiya gaya hai)
# ==========================================

# 1. Exam List Ka Route (Admin Dashboard)
@online_exams_bp.route("/")
@login_required
def index():
    # Yahan database se exams fetch karenge. Abhi ke liye khali list hai.
    exams = [] 
    classes = [10, 12] 
    
    return render_template('online_exams/index.html', exams=exams, classes=classes, selected_class=None)

# 2. Ultimate Exam Dene Ka Route
@online_exams_bp.route("/take_exam/<int:eid>")
@login_required
def take_exam(eid):
    # Abhi test ke liye dummy data bhej rahe hain (Baad mein DB se aayega)
    dummy_exam = {"id": eid, "title": "Demo Test"}
    dummy_questions = [
        {"id": 1, "type": "mcq", "text": "2 + 2 kitna hota hai?", "options": ["2", "3", "4", "5"], "correct": 2},
        {"id": 2, "type": "tf", "text": "Sun East se ugta hai.", "options": ["True", "False"], "correct": 0}
    ]

    return render_template('online_exams/ultimate-exam.html', exam=dummy_exam, questions=dummy_questions)

# 3. New Exam Add Karne ka Route
@online_exams_bp.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        pass
    return "Add Exam Form Yahan Aayega" 

# 4. Manage Exam Route
@online_exams_bp.route("/manage/<int:eid>")
@login_required
def manage(eid):
    return f"Manage Exam {eid} Yahan Aayega"

# 5. Edit Exam Route
@online_exams_bp.route("/edit/<int:eid>")
@login_required
def edit(eid):
    return f"Edit Exam {eid} Yahan Aayega"
