from datetime import date, datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required
from database import (
    check_in_visitor, check_out_visitor, get_visitor,
    get_visitors, get_visitors_summary, get_active_visitors,
    get_students, get_staff_list, VISITOR_PURPOSES
)

visitors_bp = Blueprint("visitors", __name__, url_prefix="/visitors")


@visitors_bp.route("/")
@login_required
def index():
    date_str = request.args.get("date") or date.today().isoformat()
    status = request.args.get("status", "").strip()
    search = request.args.get("q", "").strip()

    visitors = get_visitors(date_str, status or None, search or None)
    summary = get_visitors_summary(date_str)

    return render_template("visitors/index.html",
                           visitors=visitors, date=date_str,
                           selected_status=status, search=search,
                           summary=summary)


@visitors_bp.route("/check-in", methods=["GET", "POST"])
@login_required
def check_in():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("name"):
            flash("Visitor name zaroori hai", "error")
            return redirect(url_for("visitors.check_in"))
        try:
            res = check_in_visitor(data, session["admin_id"])
            flash(f"Visitor check-in — Badge {res['badge_no']}", "success")
            return redirect(url_for("visitors.badge", visitor_id=res["id"]))
        except Exception as e:
            flash(f"Error: {str(e)[:100]}", "error")
            return redirect(url_for("visitors.check_in"))

    students = []
    for s in get_students():
        students.append({
            "id": s[0], "name": s[1], "roll": s[2],
            "class_name": s[3], "section": s[4]
        })
    staff = get_staff_list()

    return render_template("visitors/check_in.html",
                           students=students, staff=staff,
                           purposes=VISITOR_PURPOSES,
                           today=date.today().isoformat())


@visitors_bp.route("/<int:visitor_id>")
@login_required
def view(visitor_id):
    v = get_visitor(visitor_id)
    if not v:
        abort(404)
    return render_template("visitors/view.html", v=v)


@visitors_bp.route("/<int:visitor_id>/badge")
@login_required
def badge(visitor_id):
    v = get_visitor(visitor_id)
    if not v:
        abort(404)
    return render_template("visitors/badge.html", v=v)


@visitors_bp.route("/<int:visitor_id>/check-out", methods=["POST"])
@login_required
def checkout(visitor_id):
    if check_out_visitor(visitor_id):
        flash("Visitor checked out", "success")
    else:
        flash("Already checked out ya not found", "error")
    return redirect(request.referrer or url_for("visitors.index"))


@visitors_bp.route("/active")
@login_required
def active():
    visitors = get_active_visitors()
    return render_template("visitors/active.html", visitors=visitors)
