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

online_exams_bp = Blueprint("online_exams", __name__, url_prefix="/online-exams")

# ==========================================
# 1. REAL ROUTES (Database ke sath)
# ==========================================

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
        
        # Validation: Title, Class aur Subject zaroori hain
        if not data.get("title") or not data.get("class_name") or not data.get("subject"):
            flash("Title, Class aur Subject zaroori hain", "error")
            return redirect(url_for("online_exams.add"))
        
        try:
            # Database function ko alag-alag arguments pass kar rahe hain
            eid = create_online_exam(
                title=data.get("title"),
                class_name=data.get("class_name"),
                subject=data.get("subject"),
                duration_minutes=int(data.get("duration_minutes") or 30),
                total_marks=int(data.get("total_marks") or 100),
                created_by=session.get("admin_id"),
                start_date=data.get("start_date") or None,
                end_date=data.get("end_date") or None,
                instructions=data.get("instructions") or None
            )
            flash("Exam create ho gaya. Ab questions add karo.", "success")
            return redirect(url_for("online_exams.manage", eid=eid))
        except Exception as e:
            flash(f"Exam create karne mein error aaya: {str(e)[:100]}", "error")
            return redirect(url_for("online_exams.add"))
            
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
        # Note: Agar edit mein bhi error aaye, toh yahan bhi alag-alag parameters pass karne padenge
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


# ==========================================
# 2. NAYA ROUTE (Exam dene ke liye)
# ==========================================

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
    # ============================================================
# 3. STUDENT EXAM SUBMIT ROUTE (Naya Add Karein)
# ============================================================
@online_exams_bp.route("/submit_exam/<int:eid>", methods=["POST"])
@login_required
def submit_exam(eid):
    # Frontend (ultimate-exam.html) se aaya hua JSON data receive karein
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400

    student_answers = data.get("answers", [])
    score = data.get("score", 0)
    
    # Yahan aap database mein save karne ka logic likhenge
    # Example: save_student_result(exam_id=eid, answers=student_answers, score=score)
    print(f"Exam ID: {eid} | Score: {score} | Answers: {student_answers}")

    # Frontend ko success message bhejein
    return jsonify({"status": "success", "message": "Exam submitted successfully!"})


# ============================================================
# 4. REAL DATABASE INTEGRATION (Future ke liye)
# ============================================================
# (Jab aapke paas real questions ka database ready ho jaye, toh take_exam route ko aise update karein)
#
# @online_exams_bp.route("/take_exam/<int:eid>")
# @login_required
# def take_exam(eid):
#     # 1. Database se exam ki details nikalein
#     # exam = get_exam_by_id(eid)
#     
#     # 2. Database se us exam ke saare questions nikalein
#     # questions = get_questions_by_exam_id(eid)
#     
#     # 3. JSON format mein convert karein
#     # formatted_questions = [
#     #     {
#     #         "id": q["id"], 
#     #         "type": q["type"], 
#     #         "text": q["question_text"], 
#     #         "options": [q["option_a"], q["option_b"], q["option_c"], q["option_d"]], 
#     #         "correct": q["correct_index"]
#     #     } for q in questions
#     # ]
#     
#     # 4. Template ko data bhejein
#     # return render_template('online_exams/ultimate-exam.html', exam=exam, questions=formatted_questions)
