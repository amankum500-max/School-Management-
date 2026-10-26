from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session
)
from modules.auth import login_required
from database import (
    create_custom_alert, get_custom_alerts,
    toggle_custom_alert, delete_custom_alert,
    get_computed_alerts
)

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")

@alerts_bp.route("/")
@login_required
def index():
    computed = get_computed_alerts()
    custom = get_custom_alerts(active_only=False, limit=50)
    return render_template("alerts/index.html",
                           computed=computed, custom=custom)

@alerts_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("title"):
            flash("Title zaroori hai", "error")
            return redirect(url_for("alerts.add"))
        create_custom_alert(data, session["admin_id"])
        flash("Alert create ho gaya", "success")
        return redirect(url_for("alerts.index"))
    return render_template("alerts/form.html")

@alerts_bp.route("/<int:aid>/toggle", methods=["POST"])
@login_required
def toggle(aid):
    is_active = request.form.get("is_active") == "1"
    toggle_custom_alert(aid, is_active)
    flash("Alert status update ho gaya", "success")
    return redirect(url_for("alerts.index"))

@alerts_bp.route("/<int:aid>/delete", methods=["POST"])
@login_required
def remove(aid):
    delete_custom_alert(aid)
    flash("Alert delete ho gaya", "success")
    return redirect(url_for("alerts.index"))
