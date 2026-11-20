from flask import Blueprint, render_template, request, redirect, url_for, flash
from modules.auth import login_required

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")


@exams_bp.route("/")
@login_required
def index():
    return render_template("exams/index.html")


@exams_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_exam():
    if request.method == "POST":
        # Yahan exam create karne ka DB logic aayega
        flash("Exam created successfully.", "success")
        return redirect(url_for("exams.index"))
    return render_template("exams/form.html")


@exams_bp.route("/marks", methods=["GET", "POST"])
@login_required
def marks_entry():
    if request.method == "POST":
        # Yahan students ke marks save karne ka DB logic aayega
        flash("Marks saved successfully.", "success")
        return redirect(url_for("exams.index"))
    return render_template("exams/marks_entry.html")


@exams_bp.route("/merit")
@login_required
def merit():
    # Yahan merit list ka data calculate/fetch karke bhejein
    return render_template("exams/merit.html")


@exams_bp.route("/report-card/<int:student_id>")
@login_required
def report_card(student_id):
    # Yahan student_id ke hisab se report card data fetch karein
    return render_template("exams/report_card.html", student_id=student_id)
