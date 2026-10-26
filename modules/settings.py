from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash
)
from modules.auth import login_required
from database import get_settings, update_settings

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        update_settings(request.form.to_dict())
        flash("Settings update ho gaye", "success")
        return redirect(url_for("settings.index"))
    return render_template("settings/index.html", settings=get_settings())
