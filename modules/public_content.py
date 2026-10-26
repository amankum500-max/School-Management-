from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash
)
from modules.auth import login_required, role_required
from database import (
    create_testimonial, get_testimonials, delete_testimonial,
    toggle_testimonial_public, create_gallery_item, get_gallery,
    delete_gallery_item
)

public_content_bp = Blueprint("public_content", __name__,
                              url_prefix="/site-content")

@public_content_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    testimonials = get_testimonials(public_only=False, limit=100)
    gallery = get_gallery(public_only=False, limit=200)
    return render_template("public_content/index.html",
                           testimonials=testimonials, gallery=gallery)

# ---------- Testimonials ----------
@public_content_bp.route("/testimonial/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def testimonial_add():
    data = request.form.to_dict()
    if not data.get("name") or not data.get("message"):
        flash("Name aur message zaroori", "error")
        return redirect(url_for("public_content.index"))
    create_testimonial(data)
    flash("Testimonial add ho gaya", "success")
    return redirect(url_for("public_content.index"))

@public_content_bp.route("/testimonial/<int:tid>/toggle", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def testimonial_toggle(tid):
    is_public = request.form.get("is_public") == "1"
    toggle_testimonial_public(tid, is_public)
    flash("Visibility update ho gayi", "success")
    return redirect(url_for("public_content.index"))

@public_content_bp.route("/testimonial/<int:tid>/delete", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def testimonial_delete(tid):
    delete_testimonial(tid)
    flash("Testimonial delete ho gaya", "success")
    return redirect(url_for("public_content.index"))

# ---------- Gallery ----------
@public_content_bp.route("/gallery/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def gallery_add():
    data = request.form.to_dict()
    if not data.get("image_url"):
        flash("Image URL zaroori hai", "error")
        return redirect(url_for("public_content.index"))
    create_gallery_item(data)
    flash("Photo add ho gayi", "success")
    return redirect(url_for("public_content.index"))

@public_content_bp.route("/gallery/<int:gid>/delete", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def gallery_delete(gid):
    delete_gallery_item(gid)
    flash("Photo delete ho gayi", "success")
    return redirect(url_for("public_content.index"))
