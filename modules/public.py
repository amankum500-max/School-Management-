from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from database import (
    get_settings, get_notices, create_enquiry
)

public_bp = Blueprint("public_site", __name__, url_prefix="/site")

@public_bp.route("/")
def home():
    s = get_settings()
    notices = [
        {"id": r[0], "title": r[1], "content": r[2], "category": r[3],
         "priority": r[4], "created_at": r[8]}
        for r in get_notices(public_only=True, limit=6)
    ]
    return render_template("public/home.html", school=s, notices=notices)

@public_bp.route("/about")
def about():
    return render_template("public/about.html", school=get_settings())

@public_bp.route("/contact")
def contact():
    return render_template("public/contact.html", school=get_settings())

@public_bp.route("/notices")
def notices_list():
    rows = get_notices(public_only=True, limit=100)
    notices = [
        {"id": r[0], "title": r[1], "content": r[2], "category": r[3],
         "priority": r[4], "created_at": r[8]}
        for r in rows
    ]
    return render_template("public/notices.html",
                           school=get_settings(), notices=notices)

@public_bp.route("/admission", methods=["GET", "POST"])
def admission():
    if request.method == "POST":
        data = request.form.to_dict()
        # Basic validation
        if not data.get("student_name") or not data.get("parent_name") \
           or not data.get("parent_phone"):
            flash("Student name, parent name, aur phone zaroori hain", "error")
            return redirect(url_for("public_site.admission"))

        phone = data["parent_phone"].strip()
        if len(phone) < 10:
            flash("Sahi 10-digit phone number daalo", "error")
            return redirect(url_for("public_site.admission"))

        try:
            eid = create_enquiry(data)
            return render_template("public/admission_success.html",
                                   school=get_settings(), enquiry_id=eid)
        except Exception as e:
            flash(f"Error: Kuch galat hua. Dobara try karo.", "error")
            return redirect(url_for("public_site.admission"))

    return render_template("public/admission.html", school=get_settings())
