from flask import (
    Blueprint, render_template, request, abort
)
from modules.auth import login_required
from modules.help_data import HELP_TOPICS, HELP_CATEGORIES

help_bp = Blueprint("help", __name__, url_prefix="/help")

# URL prefix → help slug mapping
HELP_SLUG_BY_PREFIX = [
    ("/students", "students"),
    ("/fees", "fees"),
    ("/bills", "fees"),
    ("/attendance", "attendance"),
    ("/qr-attendance", "qr-attendance"),
    ("/exams", "exams"),
    ("/notices", "communication"),
    ("/events", "communication"),
    ("/homework", "homework"),
    ("/staff", "staff"),
    ("/teachers-admin", "staff"),
    ("/teacher/", "teacher-portal"),
    ("/salary", "finance"),
    ("/expenses", "finance"),
    ("/reports", "reports"),
    ("/whatsapp", "whatsapp"),
    ("/backup", "backup"),
    ("/admin-users", "multi-admin"),
    ("/settings", "settings"),
    ("/medical", "medical"),
    ("/library", "library"),
    ("/transport", "transport"),
    ("/hostel", "hostel"),
    ("/promotion", "promotion"),
    ("/certificates", "certificates"),
    ("/alerts", "alerts"),
]

def get_help_slug(path):
    for prefix, slug in HELP_SLUG_BY_PREFIX:
        if path.startswith(prefix):
            return slug
    return None

@help_bp.route("/")
@login_required
def index():
    """Help center landing page"""
    q = request.args.get("q", "").strip().lower()

    # Group topics by category
    grouped = []
    for cat in HELP_CATEGORIES:
        topics_in_cat = []
        for slug, topic in HELP_TOPICS.items():
            if topic["category"] != cat["id"]:
                continue
            if q:
                # Search filter
                searchable = (topic["title"] + " " + topic["summary"] +
                              " " + " ".join(topic.get("steps", []))).lower()
                if q not in searchable:
                    continue
            topics_in_cat.append({**topic, "slug": slug})
        if topics_in_cat:
            grouped.append({"id": cat["id"], "label": cat["label"],
                            "topics": topics_in_cat})

    total = sum(len(g["topics"]) for g in grouped)
    return render_template("help/index.html",
                           grouped=grouped, query=q, total=total)

@help_bp.route("/<slug>")
@login_required
def topic(slug):
    t = HELP_TOPICS.get(slug)
    if not t:
        abort(404)
    # Find related topics
    related = []
    for rel_slug in t.get("related", []):
        if rel_slug in HELP_TOPICS:
            related.append({**HELP_TOPICS[rel_slug], "slug": rel_slug})
    return render_template("help/topic.html",
                           topic=t, slug=slug, related=related)

@help_bp.route("/getting-started")
@login_required
def getting_started():
    """Shortcut to getting-started topic"""
    return topic("getting-started")
