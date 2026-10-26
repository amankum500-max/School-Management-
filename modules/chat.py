from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, abort
)
from modules.auth import login_required, role_required
from database import (
    get_admin_threads, get_thread, get_thread_messages,
    post_message, mark_thread_read, close_thread, reopen_thread,
    count_unread_threads_for_admin, get_parent_info,
    get_students, get_parent_threads
)

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/")
@login_required
@role_required("super_admin", "admin")
def index():
    status = request.args.get("status", "").strip()
    search = request.args.get("q", "").strip()
    threads = get_admin_threads(status=status or None, search=search or None)
    unread_total = count_unread_threads_for_admin()
    return render_template("chat/index.html",
                           threads=threads, selected_status=status,
                           search=search, unread_total=unread_total)


@chat_bp.route("/<int:thread_id>", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def view(thread_id):
    thread = get_thread(thread_id)
    if not thread:
        abort(404)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            post_message(thread_id, "admin", session["admin_id"],
                         session.get("admin_name", "Admin"), body)
        return redirect(url_for("chat.view", thread_id=thread_id))

    # Mark read on GET
    mark_thread_read(thread_id, "admin")
    messages = get_thread_messages(thread_id)

    return render_template("chat/view.html",
                           thread=thread, messages=messages)


@chat_bp.route("/<int:thread_id>/send", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def send_ajax(thread_id):
    """AJAX endpoint for quick replies"""
    data = request.json or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"ok": False, "error": "Empty message"}), 400
    mid = post_message(thread_id, "admin", session["admin_id"],
                        session.get("admin_name", "Admin"), body)
    return jsonify({"ok": True, "message_id": mid})


@chat_bp.route("/<int:thread_id>/close", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def close(thread_id):
    close_thread(thread_id)
    flash("Thread closed", "success")
    return redirect(url_for("chat.view", thread_id=thread_id))


@chat_bp.route("/<int:thread_id>/reopen", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def reopen(thread_id):
    reopen_thread(thread_id)
    flash("Thread reopened", "success")
    return redirect(url_for("chat.view", thread_id=thread_id))


@chat_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def new_thread():
    """Admin initiates conversation with a parent"""
    from database import get_conn

    if request.method == "POST":
        parent_id = request.form.get("parent_id", type=int)
        student_id = request.form.get("student_id", type=int)
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not parent_id or not body:
            flash("Parent aur message zaroori hai", "error")
            return redirect(url_for("chat.new_thread"))

        parent = get_parent_info(parent_id)
        pname = parent["name"] if parent else "Parent"

        from database import create_message_thread

        # Create thread but from admin — special case
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO message_threads
            (parent_id, student_id, subject, last_message_by, unread_by_parent)
            VALUES (%s, %s, %s, 'admin', 1) RETURNING id;
        """, (parent_id, student_id, subject or "Message from school"))
        tid = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO messages
            (thread_id, sender_type, sender_id, sender_name, body)
            VALUES (%s, 'admin', %s, %s, %s);
        """, (tid, session["admin_id"], session.get("admin_name", "Admin"), body))
        conn.commit()
        cur.close()
        conn.close()

        flash("Message sent to parent", "success")
        return redirect(url_for("chat.view", thread_id=tid))

    # GET — list parents
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.phone,
               (SELECT COUNT(*) FROM message_threads
                WHERE parent_id=p.id AND unread_by_parent > 0) AS unread
        FROM parents p
        ORDER BY p.name NULLS LAST LIMIT 100;
    """)
    parents = [{"id": r[0], "name": r[1] or r[2], "phone": r[2],
                "unread": r[3] or 0} for r in cur.fetchall()]
    cur.close()
    conn.close()

    return render_template("chat/new.html", parents=parents)
