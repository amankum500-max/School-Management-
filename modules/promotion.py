from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    get_class_roster, promote_students, log_promotion,
    get_promotion_logs, get_class_count_summary,
    get_next_class, get_classes_list, CLASS_SEQUENCE
)

promotion_bp = Blueprint("promotion", __name__, url_prefix="/promotion")

def _academic_year():
    now = datetime.now()
    y = now.year
    if now.month >= 4:
        return f"{y}-{str(y+1)[-2:]}"
    return f"{y-1}-{str(y)[-2:]}"

@promotion_bp.route("/")
@login_required
def index():
    classes = CLASS_SEQUENCE
    summary = get_class_count_summary()
    logs = get_promotion_logs(10)
    return render_template(
        "promotion/index.html",
        classes=classes,
        summary=summary,
        logs=logs
    )

@promotion_bp.route("/preview")
@login_required
def preview():
    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    if not class_name:
        flash("Class select karo", "error")
        return redirect(url_for("promotion.index"))

    students = get_class_roster(class_name, section or None)
    next_class = get_next_class(class_name)

    return render_template(
        "promotion/preview.html",
        class_name=class_name,
        section=section,
        students=students,
        next_class=next_class,
        is_last_class=(next_class == "ALUMNI"),
        current_ay=_academic_year()
    )

@promotion_bp.route("/execute", methods=["POST"])
@login_required
def execute():
    class_name = request.form.get("class_name", "").strip()
    section = request.form.get("section", "").strip()

    if not class_name:
        flash("Class missing", "error")
        return redirect(url_for("promotion.index"))

    # Get all students again for validation
    roster = get_class_roster(class_name, section or None)
    valid_ids = {s["id"] for s in roster}

    # Collect student IDs by action
    promote_ids = []
    repeat_ids = []
    archive_ids = []

    for s in roster:
        action = request.form.get(f"action_{s['id']}", "promote")
        if s["id"] not in valid_ids:
            continue
        if action == "promote":
            promote_ids.append(s["id"])
        elif action == "repeat":
            repeat_ids.append(s["id"])
        elif action == "archive":
            archive_ids.append(s["id"])

    if not (promote_ids or repeat_ids or archive_ids):
        flash("Koi student select nahi kiya", "error")
        return redirect(url_for("promotion.preview", **{"class": class_name, "section": section}))

    next_class = get_next_class(class_name)
    if not next_class and promote_ids:
        flash("Class progression define nahi hai is class ka", "error")
        return redirect(url_for("promotion.index"))

    # Execute
    try:
        result_promoted = {"updated": 0}
        result_repeated = {"updated": 0}
        result_archived = {"updated": 0}

        if promote_ids and next_class and next_class != "ALUMNI":
            result_promoted = promote_students(promote_ids, next_class, "promote")
        elif promote_ids and next_class == "ALUMNI":
            # Last class — archive karo
            result_archived = promote_students(promote_ids, class_name, "archive")
            archive_ids = list(set(archive_ids + promote_ids))

        if repeat_ids:
            result_repeated = promote_students(repeat_ids, class_name, "repeat")

        if archive_ids:
            result_archived = promote_students(archive_ids, class_name, "archive")

        total = len(promote_ids) + len(repeat_ids) + len(archive_ids)
        log_promotion(
            class_name, next_class or "ALUMNI",
            _academic_year(), total,
            result_promoted["updated"],
            result_repeated["updated"],
            result_archived["updated"],
            session["admin_id"]
        )

        flash(
            f"Promotion complete — "
            f"{result_promoted['updated']} promoted, "
            f"{result_repeated['updated']} repeated, "
            f"{result_archived['updated']} archived",
            "success"
        )
        return redirect(url_for("promotion.index"))

    except Exception as e:
        flash(f"Error: {e}", "error")
        return redirect(url_for("promotion.preview", **{"class": class_name, "section": section}))

@promotion_bp.route("/logs")
@login_required
def logs():
    all_logs = get_promotion_logs(200)
    return render_template("promotion/logs.html", logs=all_logs)
