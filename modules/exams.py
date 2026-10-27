from flask import Blueprint, render_template
from modules.auth import login_required

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")

@exams_bp.route("/")
@login_required
def index():
    return "Exams Module is loading successfully."
