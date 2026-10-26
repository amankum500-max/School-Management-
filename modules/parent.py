from database import (
    ...,
    create_message_thread, get_parent_threads,
    get_thread, get_thread_messages, post_message,
    mark_thread_read, count_unread_threads_for_parent,
    get_parent_info,
)
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from database import (
    create_parent, verify_parent, phone_exists_in_students,
    get_children_for_parent, get_student,
    get_attendance_summary, get_attendance_calendar,
    get_payments, pending_amount_for_student,
    get_exams_for_class, get_student_marks_report,
    get_notices_for_class
)

parent_bp = Blueprint("parent", __name__, url_prefix="/parent")

def parent_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "parent_id" not in session:
            return redirect(url_for("parent.login"))
        return f(*args, **kwargs)
    return wrapper
    from database import (
    ...,
    get_upcoming_events
)

# ---------- Auth ----------
@parent_bp.route("/register", methods=["GET", "POST"])
def register():
    if "parent_id" in session:
        return redirect(url_for("parent.dashboard"))

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if len(password) < 6:
            flash("Password kam se kam 6 characters ka hona chahiye", "error")
            return redirect(url_for("parent.register"))

        if not phone_exists_in_students(phone):
            flash("Ye phone number kisi student ke parent ke roop mein registered nahi hai. School office se sampark karo.", "error")
            return redirect(url_for("parent.register"))

        try:
            create_parent(phone, password, name)
            flash("Account ban gaya. Ab login karo.", "success")
            return redirect(url_for("parent.login"))
        except Exception as e:
            flash(f"Error: Ye phone already registered hai, ya kuch galat hua.", "error")
            return redirect(url_for("parent.register"))

    return render_template("parent/register.html")

@parent_bp.route("/login", methods=["GET", "POST"])
def login():
    if "parent_id" in session:
        return redirect(url_for("parent.dashboard"))

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        p = verify_parent(phone, password)
        if p:
            session["parent_id"] = p["id"]
            session["parent_phone"] = p["phone"]
            session["parent_name"] = p["name"] or p["phone"]
            return redirect(url_for("parent.dashboard"))
        flash("Galat phone ya password", "error")
    return render_template("parent/login.html")

@parent_bp.route("/logout")
def logout():
    for k in ["parent_id", "parent_phone", "parent_name"]:
        session.pop(k, None)
    return redirect(url_for("parent.login"))

# ---------- Dashboard ----------
@parent_bp.route("/")
@parent_required
def dashboard():
    children = get_children_for_parent(session["parent_phone"])
    if not children:
        flash("Koi student record nahi mila aapke phone se.", "error")

    month = datetime.now().strftime("%Y-%m")
    cards = []
    for c in children:
        att = get_attendance_summary(c["id"], month)
        pending = pending_amount_for_student(c["id"], month)
        cards.append({**c, "attendance_percent": att["percent"], "pending_fees": pending})

    return render_template("parent/dashboard.html", children=cards, month=month)
    @parent_bp.route("/events")
@parent_required
def events():
    children = get_children_for_parent(session["parent_phone"])
    if not children:
        return render_template("parent/events.html", events=[], selected=None)

    child_id = request.args.get("child_id", type=int)
    selected = None
    if child_id:
        for c in children:
            if c["id"] == child_id:
                selected = c
                break
    if not selected:
        selected = children[0]

    evs = get_upcoming_events(days=60, class_name=selected["class_name"] or "", limit=30)
    return render_template("parent/events.html",
                           events=evs, children=children, selected=selected)

# ---------- Child detail ----------
@parent_bp.route("/child/<int:student_id>")
@parent_required
def child_detail(student_id):
    # Verify ye child is parent's
    children = get_children_for_parent(session["parent_phone"])
    child_ids = [c["id"] for c in children]
    if student_id not in child_ids:
        abort(403)

    row = get_student(student_id)
    if not row:
        abort(404)
    keys = ["id","name","roll_no","class_name","section","gender","dob",
            "parent_name","parent_phone","address","admission_date","status","created_at"]
    student = dict(zip(keys, row))

    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    att_summary = get_attendance_summary(student_id, month)
    att_calendar = get_attendance_calendar(student_id, month)
    pending = pending_amount_for_student(student_id, month)
    payments = [
        {"id": r[0], "fee_type": r[5], "amount": r[6], "month": r[7],
         "mode": r[8], "receipt_no": r[9], "paid_at": r[10]}
        for r in get_payments(student_id=student_id, limit=50)
    ]

    exams = get_exams_for_class(student["class_name"]) if student["class_name"] else []
    exam_results = []
    for e in exams:
        marks = get_student_marks_report(e["id"], student_id)
        if not marks:
            continue
        total = sum(v for v in marks.values() if v is not None)
        max_total = e["max_marks"] * len(e["subjects"])
        percent = round((total / max_total) * 100, 1) if max_total else 0
        exam_results.append({
            "exam": e, "marks": marks, "total": total,
            "max_total": max_total, "percent": percent
        })

    return render_template(
        "parent/child_detail.html",
        student=student,
        month=month,
        att_summary=att_summary,
        att_calendar=att_calendar,
        pending_fees=pending,
        payments=payments,
        exam_results=exam_results
    )

# ---------- Notices ----------
@parent_bp.route("/notices")
@parent_required
def notices():
    children = get_children_for_parent(session["parent_phone"])
    if not children:
        return render_template("parent/notices.html", notices=[], classes=[])
    # Combine notices for all children's classes (dedupe)
    all_notices = {}
    for c in children:
        for n in get_notices_for_class(c["class_name"] or ""):
            all_notices[n["id"]] = n
    notices_list = sorted(
        all_notices.values(),
        key=lambda x: (x["priority"] == "urgent", x["priority"] == "high", x["created_at"]),
        reverse=True
    )
    return render_template("parent/notices.html", notices=notices_list)
    @parent_bp.route("/homework")
@parent_required
def homework_list():
    children = get_children_for_parent(session["parent_phone"])
    if not children:
        return render_template("parent/homework.html", children=[], selected_id=None)

    # Query string se child_id, ya pehla child
    child_id = request.args.get("child_id", type=int)
    selected = None
    if child_id:
        for c in children:
            if c["id"] == child_id:
                selected = c
                break
    if not selected and children:
        selected = children[0]

    hw = []
    if selected:
        hw = get_homework_for_class(selected["class_name"] or "",
                                    selected["section"] or "")

    from datetime import date
    today = date.today()
    for h in hw:
        if h["due_date"]:
            if h["due_date"] < today:
                h["status"] = "overdue"
            elif h["due_date"] == today:
                h["status"] = "today"
            else:
                h["status"] = "upcoming"
        else:
            h["status"] = "no_due"

    return render_template("parent/homework.html",
                           children=children, selected=selected, homework=hw)
    from database import get_student_fee_dues, get_online_payments_for_student

@parent_bp.route("/child/<int:student_id>")
@parent_required
def child_detail(student_id):
    children = get_children_for_parent(session["parent_phone"])
    if student_id not in [c["id"] for c in children]:
        abort(403)

    row = get_student(student_id)
    # ... existing code ...
    pending = pending_amount_for_student(student_id, month)
    online_payments = get_online_payments_for_student(student_id, limit=10)  # ← NEW
    
    return render_template(
        "parent/child_detail.html",
        student=student,
        month=month,
        # ... existing ...
        online_payments=online_payments    # ← NEW
    )
@parent_bp.route("/messages")
@parent_required
def messages_list():
    parent_id = session.get("parent_id")
    threads = get_parent_threads(parent_id)
    unread = count_unread_threads_for_parent(parent_id)
    return render_template("parent/messages_list.html",
                           threads=threads, unread=unread)


@parent_bp.route("/messages/new", methods=["GET", "POST"])
@parent_required
def messages_new():
    parent_id = session.get("parent_id")
    children = get_children_for_parent(session["parent_phone"])

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not body:
            flash("Message khaali nahi ho sakta", "error")
            return redirect(url_for("parent.messages_new"))

        parent = get_parent_info(parent_id)
        pname = parent["name"] if parent else "Parent"

        tid = create_message_thread(
            parent_id, student_id, subject, body, pname
        )
        flash("Message sent", "success")
        return redirect(url_for("parent.messages_thread", thread_id=tid))

    return render_template("parent/messages_new.html",
                           children=children)


@parent_bp.route("/messages/<int:thread_id>", methods=["GET", "POST"])
@parent_required
def messages_thread(thread_id):
    thread = get_thread(thread_id)
    if not thread:
        abort(404)
    # Security — must be parent's own thread
    if thread["parent_id"] != session.get("parent_id"):
        abort(403)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            parent = get_parent_info(session["parent_id"])
            pname = parent["name"] if parent else "Parent"
            post_message(thread_id, "parent", session["parent_id"],
                         pname, body)
        return redirect(url_for("parent.messages_thread",
                                thread_id=thread_id))

    mark_thread_read(thread_id, "parent")
    messages = get_thread_messages(thread_id)
    return render_template("parent/messages_thread.html",
                           thread=thread, messages=messages)
