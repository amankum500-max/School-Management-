from flask import Blueprint, render_template, request, redirect, url_for
from modules.auth import login_required
# Agar aapke paas models hain toh unhe import karein (example)
# from models import Exam, Question

# DHYAN DEIN: Blueprint ka naam "online_exams" rakha hai taaki HTML ke url_for se match kare
exams_bp = Blueprint("online_exams", __name__, url_prefix="/online_exams")

# 1. Exam List Ka Route (Admin Dashboard)
@exams_bp.route("/")
@login_required
def index():
    # Yahan database se exams fetch karenge. Abhi ke liye humne dummy list banayi hai.
    # exams = Exam.query.all()
    
    exams = [] # Filhaal khali list, yahan DB se data aayega
    classes = [10, 12] # Dummy classes
    
    return render_template('online_exams/index.html', exams=exams, classes=classes, selected_class=None)

# 2. Ultimate Exam Dene Ka Route
@exams_bp.route("/take_exam/<int:eid>")
@login_required
def take_exam(eid):
    # Database se exam aur uske questions fetch karein
    # exam = Exam.query.get_or_404(eid)
    # questions_db = Question.query.filter_by(exam_id=eid).all()
    # questions = [q.to_dict() for q in questions_db]

    # Abhi test ke liye dummy data bhej rahe hain
    dummy_exam = {"id": eid, "title": "Demo Test"}
    dummy_questions = [
        {"id": 1, "type": "mcq", "text": "2 + 2 kitna hota hai?", "options": ["2", "3", "4", "5"], "correct": 2},
        {"id": 2, "type": "tf", "text": "Sun East se ugta hai.", "options": ["True", "False"], "correct": 0}
    ]

    return render_template('online_exams/ultimate-exam.html', exam=dummy_exam, questions=dummy_questions)


# 3. New Exam Add Karne ka Route (Placeholder)
@exams_bp.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # Form ka data save karne ka logic yahan aayega
        pass
    return "Add Exam Form Yahan Aayega" # Baad mein isko form.html se replace karein

# 4. Manage Exam Route (Placeholder)
@exams_bp.route("/manage/<int:eid>")
@login_required
def manage(eid):
    return f"Manage Exam {eid} Yahan Aayega"

# 5. Edit Exam Route (Placeholder)
@exams_bp.route("/edit/<int:eid>")
@login_required
def edit(eid):
    return f"Edit Exam {eid} Yahan Aayega"
