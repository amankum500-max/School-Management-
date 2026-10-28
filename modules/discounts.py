from datetime import date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required, role_required

# ✅ FIX: get_discount_type (singular) hata diya gaya hai kyunki ye use nahi ho raha tha aur error de raha tha.
# ✅ Saare imports ek jagah par clean kar diye gaye hain.
from database import (
    get_discount_types, create_discount_type, delete_discount_type,
    get_student_discounts, add_student_discount, remove_student_discount,
    compute_student_discount, get_discounts_summary_for_class,
    get_all_discount_summary, get_student, get_students,
    DISCOUNT_CATEGORIES, get_conn, get_classes_list
)

discounts_bp = Blueprint("discounts", __name__, url_prefix="/discounts")

@discounts_bp.route("/")
@login_required
@role_required("super_admin", "admin", "accountant")
def index():
    types = get_discount_types(active_only=False)
    summary = get_all_discount_summary()
    return render_template("discounts/index.html",
                           types=types, summary=summary,
                           categories=DISCOUNT_CATEGORIES)

@discounts_bp.route("/types/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_type():
    data = request.form
    name = data.get("name", "").strip()
    if not name:
        flash("Name zaroori hai", "error")
        return redirect(url_for("discounts.index"))
    try:
        create_discount_type(
            name,
            data.get("category") or "other",
            data.get("discount_type") or "percent",
            float(data.get("value") or 0),
            data.get("description") or ""
        )
        flash("Discount type create ho gaya", "success")
    except Exception as e:
        # ✅ FIX: Bare 'except' ki jagah actual error print karein taaki debugging aasan ho.
        print(f"Error creating discount type: {e}") 
        flash("Naam already exists ya kuch galat hua", "error")
    return redirect(url_for("discounts.index"))

@discounts_bp.route("/types/<int:dtid>/delete", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete_type(dtid):
    delete_discount_type(dtid)
    flash("Discount type delete ho gaya", "success")
    return redirect(url_for("discounts.index"))

# ---------- Student discounts ----------
@discounts_bp.route("/student/<int:student_id>")
@login_required
@role_required("super_admin", "admin", "accountant")
def student_view(student_id):
    row = get_student(student_id)
    if not row:
        abort(404)
        
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))

    applied = get_student_discounts(student_id, active_only=False)
    types = get_discount_types()

    # Current fee base — for preview
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM fee_structure
            WHERE class_name=%s;
        """, (student["class_name"],))
        base_fee = float(cur.fetchone()[0] or 0)
    finally:
        # ✅ FIX: Database connection ko hamesha close karein, chahe error aaye ya na aaye.
        cur.close()
        conn.close()

    discount_amt, discount_items = compute_student_discount(base_fee, student_id)

    return render_template("discounts/student.html",
                           student=student,
                           applied=applied,
                           types=types,
                           base_fee=base_fee,
                           discount_amt=discount_amt,
                           discount_items=discount_items,
                           final_fee=max(base_fee - discount_amt, 0),
                           today=date.today().isoformat())

@discounts_bp.route("/student/<int:student_id>/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_student(student_id):
    data = request.form
    try:
        dtid = int(data.get("discount_type_id"))
        custom = data.get("custom_value") or None
        add_student_discount(
            student_id, dtid,
            float(custom) if custom else None,
            data.get("from_date") or None,
            data.get("to_date") or None,
            data.get("reason") or "",
            session.get("admin_id") # ✅ FIX: session['admin_id'] ki jagah .get() use kiya taaki KeyError na aaye
        )
        flash("Discount apply ho gaya", "success")
    except Exception as e:
        print(f"Error adding discount: {e}")
        flash(f"Error: {e}", "error")
    return redirect(url_for("discounts.student_view", student_id=student_id))

@discounts_bp.route("/student/<int:student_id>/<int:sd_id>/remove", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def remove_student_discount_route(student_id, sd_id):
    remove_student_discount(sd_id)
    flash("Discount remove ho gaya", "success")
    return redirect(url_for("discounts.student_view", student_id=student_id))

# ---------- Reports ----------
@discounts_bp.route("/report")
@login_required
@role_required("super_admin", "admin", "accountant")
def report():
    class_name = request.args.get("class", "").strip()
    results = []
    if class_name:
        results = get_discounts_summary_for_class(class_name)
        
    return render_template("discounts/report.html",
                           results=results,
                           classes=get_classes_list(), # ✅ FIX: Import upar shift kar diya hai
                           selected_class=class_name)
