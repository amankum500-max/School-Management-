from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from database import (
    get_settings, get_notices, create_enquiry,
    get_upcoming_events                    # ← NEW
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
@public_bp.route("/")
def home():
    s = get_settings()
    notices = [...]
    events = get_upcoming_events(days=30, limit=5)   # ← NEW
    return render_template("public/home.html",
                           school=s, notices=notices, events=events)
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
    # modules/public.py — existing file mein replace/add

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from database import (
    get_settings, get_notices, create_enquiry,
    get_upcoming_events,
    get_testimonials, get_gallery, get_gallery_categories,   # ← NEW
    get_staff_list                                            # ← NEW
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
    events = get_upcoming_events(days=30, limit=5)
    testimonials = get_testimonials(public_only=True, limit=3)   # ← NEW
    gallery_preview = get_gallery(public_only=True, limit=6)      # ← NEW
    return render_template("public/home.html",
                           school=s, notices=notices, events=events,
                           testimonials=testimonials,
                           gallery_preview=gallery_preview)

@public_bp.route("/about")
def about():
    s = get_settings()
    testimonials = get_testimonials(public_only=True, limit=6)
    return render_template("public/about.html",
                           school=s, testimonials=testimonials)

@public_bp.route("/faculty")
def faculty():
    s = get_settings()
    staff = get_staff_list()      # all active staff
    # Group by role
    teachers = [x for x in staff if x["role"] in ("teacher", "principal")]
    others = [x for x in staff if x["role"] not in ("teacher", "principal")]
    return render_template("public/faculty.html",
                           school=s, teachers=teachers, others=others)

@public_bp.route("/gallery")
def gallery_page():
    s = get_settings()
    category = request.args.get("category", "").strip()
    items = get_gallery(public_only=True, category=category or None)
    cats = get_gallery_categories()
    return render_template("public/gallery.html",
                           school=s, items=items,
                           categories=cats, selected=category)

@public_bp.route("/contact")
def contact():
    return render_template("public/contact.html", school=get_settings())

# ... rest unchanged (notices_list, admission)
