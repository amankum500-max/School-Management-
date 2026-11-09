from flask import Blueprint, render_template

# ब्लूप्रिंट डिफाइन करें
exams_bp = Blueprint('exams', __name__, url_prefix='/exams')

@exams_bp.route('/')
def index():
    return "Exams Module is under construction" # बाद में इसे render_template से बदलें
