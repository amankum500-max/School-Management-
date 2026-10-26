from datetime import date, timedelta
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    create_book, get_books, get_book, update_book, delete_book,
    create_book_issue, return_book_issue, get_active_issues,
    get_issue_history, get_student_library_history,
    get_library_stats, get_student, get_students, BOOK_CATEGORIES
)

library_bp = Blueprint("library", __name__, url_prefix="/library")

@library_bp.route("/")
@login_required
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    only_available = request.args.get("available") == "1"

    books = get_books(search or None, category or None, only_available)
    stats = get_library_stats()

    return render_template("library/index.html",
                           books=books, stats=stats,
                           categories=BOOK_CATEGORIES,
                           selected_category=category,
                           search=search, only_available=only_available)

# ---------- Books CRUD ----------
@library_bp.route("/books/add", methods=["GET", "POST"])
@login_required
def book_add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("title"):
            flash("Title zaroori hai", "error")
            return redirect(url_for("library.book_add"))
        bid = create_book(data)
        flash("Book add ho gayi", "success")
        return redirect(url_for("library.book_view", bid=bid))
    return render_template("library/book_form.html",
                           book=None, mode="add",
                           categories=BOOK_CATEGORIES)

@library_bp.route("/books/<int:bid>")
@login_required
def book_view(bid):
    b = get_book(bid)
    if not b:
        abort(404)
    # Currently issued copies
    issues = [i for i in get_active_issues() if i["book_id"] == bid]
    return render_template("library/book_view.html", b=b, issues=issues)

@library_bp.route("/books/<int:bid>/edit", methods=["GET", "POST"])
@login_required
def book_edit(bid):
    b = get_book(bid)
    if not b:
        abort(404)
    if request.method == "POST":
        update_book(bid, request.form.to_dict())
        flash("Book update ho gayi", "success")
        return redirect(url_for("library.book_view", bid=bid))
    return render_template("library/book_form.html",
                           book=b, mode="edit",
                           categories=BOOK_CATEGORIES)

@library_bp.route("/books/<int:bid>/delete", methods=["POST"])
@login_required
def book_remove(bid):
    if delete_book(bid):
        flash("Book delete ho gayi", "success")
    else:
        flash("Active issues hain — pehle return karo", "error")
    return redirect(url_for("library.index"))

# ---------- Issue ----------
@library_bp.route("/issue", methods=["GET", "POST"])
@login_required
def issue():
    preselect_book = request.args.get("book_id", type=int)

    if request.method == "POST":
        book_id = request.form.get("book_id", type=int)
        student_id = request.form.get("student_id", type=int)
        due_date = request.form.get("due_date") or (date.today() + timedelta(days=14)).isoformat()
        note = request.form.get("note") or ""

        if not book_id or not student_id:
            flash("Book aur student zaroori hain", "error")
            return redirect(url_for("library.issue"))

        try:
            iid = create_book_issue(book_id, student_id, due_date, note, session["admin_id"])
            flash("Book issue ho gayi", "success")
            return redirect(url_for("library.active_issues"))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("library.issue"))

    books = get_books(only_available=True)
    students = [{"id": s[0], "name": s[1], "roll": s[2],
                 "class_name": s[3], "section": s[4]} for s in get_students()]
    default_due = (date.today() + timedelta(days=14)).isoformat()
    return render_template("library/issue.html",
                           books=books, students=students,
                           preselect_book=preselect_book,
                           default_due=default_due)

@library_bp.route("/active")
@login_required
def active_issues():
    search = request.args.get("q", "").strip()
    only_overdue = request.args.get("overdue") == "1"
    issues = get_active_issues(search or None, only_overdue)
    stats = get_library_stats()
    return render_template("library/active.html",
                           issues=issues, stats=stats,
                           search=search, only_overdue=only_overdue)

@library_bp.route("/return/<int:iid>", methods=["POST"])
@login_required
def return_book(iid):
    res = return_book_issue(iid, session["admin_id"])
    if res is None:
        flash("Return fail — record nahi mila ya already returned", "error")
    else:
        if res["fine"] > 0:
            flash(f"Book return — fine ₹{res['fine']:.0f} collect karo", "success")
        else:
            flash("Book return ho gayi (no fine)", "success")
    return redirect(url_for("library.active_issues"))

@library_bp.route("/history")
@login_required
def history():
    hist = get_issue_history(200)
    return render_template("library/history.html", history=hist)
