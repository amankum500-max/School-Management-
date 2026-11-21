from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from modules.auth import login_required, role_required
from supabase_client import get_conn as get_db_connection
import math

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")

# ==========================================
# 1. EXAMS DASHBOARD
# ==========================================
@exams_bp.route("/")
@login_required
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    exams_list = cursor.fetchall()
    conn.close()
    return render_template("exams/index.html", exams=exams_list)

@exams_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_exam():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        class_name = (request.form.get("class_name") or "").strip()

        if not name or not class_name:
            conn.close()
            flash("Exam Name aur Class zaroori hai!", "error")
            return redirect(url_for("exams.create_exam"))

        cursor.execute(
            "INSERT INTO exams (name, class_name) VALUES (%s, %s)",
            (name, class_name),
        )
        conn.commit()
        conn.close()

        flash("Exam created successfully.", "success")
        return redirect(url_for("exams.index"))
    cursor.execute("SELECT DISTINCT class_name FROM students WHERE class_name IS NOT NULL ORDER BY class_name")
    rows = cursor.fetchall()
    conn.close()

    classes = []
    for r in rows:
        val = r.get("class_name") if isinstance(r, dict) else r[0]
        if val:
            classes.append(val)

    if not classes:
        classes = ["Class 1", "Class 2", "Class 3", "Class 4", "Class 5", "Class 6", "Class 7", "Class 8", "Class 9", "Class 10"]
    return render_template("exams/form.html", classes=classes)

# ==========================================
# 2. SMART MARKS ENTRY (AJAX Enabled)
# ==========================================
@exams_bp.route("/marks/<int:exam_id>", methods=["GET"])
@login_required
def marks_entry(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        flash("Exam nahi mila.", "error")
        return redirect(url_for("exams.index"))

    cursor.execute(
        "SELECT * FROM students WHERE class_name = %s ORDER BY roll_no ASC",
        (exam["class_name"],),
    )
    students = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM subjects WHERE class_name = %s",
        (exam["class_name"],),
    )
    subjects = cursor.fetchall()

    cursor.execute(
        "SELECT student_id, subject_name, marks_obtained, is_absent FROM marks WHERE exam_id = %s",
        (exam_id,),
    )
    marks_raw = cursor.fetchall()
    conn.close()

    existing_marks = {(m["student_id"], m["subject_name"]): m for m in marks_raw}

    return render_template(
        "exams/marks_entry.html",
        exam=exam,
        students=students,
        subjects=subjects,
        existing_marks=existing_marks,
    )

@exams_bp.route("/api/save-mark", methods=["POST"])
@login_required
def api_save_mark():
    """AJAX route jisse page reload kiye bina marks save honge"""
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    exam_id = data.get("exam_id")
    subject = data.get("subject")
    marks = data.get("marks")
    is_absent = bool(data.get("is_absent", False))

    if not student_id or not exam_id or not subject:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if marks == "" or marks is None or is_absent:
        marks = 0
    else:
        try:
            marks = float(marks)
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid marks value"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM marks WHERE student_id = %s AND exam_id = %s AND subject_name = %s",
        (student_id, exam_id, subject),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE marks SET marks_obtained = %s, is_absent = %s WHERE id = %s",
            (marks, is_absent, existing["id"]),
        )
    else:
        cursor.execute(
            "INSERT INTO marks (student_id, exam_id, subject_name, marks_obtained, is_absent) VALUES (%s, %s, %s, %s, %s)",
            (student_id, exam_id, subject, marks, is_absent),
        )

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Mark saved"})

# ==========================================
# 3. MERIT LIST (With Class Rank)
# ==========================================
@exams_bp.route("/merit/<int:exam_id>")
@login_required
def merit(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        flash("Exam nahi mila.", "error")
        return redirect(url_for("exams.index"))

    cursor.execute(
        """
        SELECT s.id, s.name, s.roll_no, COALESCE(SUM(m.marks_obtained), 0) AS total_obtained
        FROM students s
        JOIN marks m ON s.id = m.student_id
        WHERE m.exam_id = %s AND s.class_name = %s AND m.is_absent = FALSE
        GROUP BY s.id, s.name, s.roll_no
        ORDER BY total_obtained DESC, s.roll_no ASC
        """,
        (exam_id, exam["class_name"]),
    )
    merit_list = cursor.fetchall()
    conn.close()

    return render_template("exams/merit.html", exam=exam, merit_list=merit_list)

# ==========================================
# 4. ULTIMATE REPORT CARD (A4 Print Ready)
# ==========================================
@exams_bp.route("/report-card/<int:student_id>/<int:exam_id>")
@login_required
def report_card(student_id, exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
    exam = cursor.fetchone()

    if not student or not exam:
        conn.close()
        flash("Record not found", "error")
        return redirect(url_for("exams.index"))

    cursor.execute(
        """
        SELECT m.subject_name, m.marks_obtained, m.is_absent, sub.max_marks
        FROM marks m
        LEFT JOIN subjects sub
            ON sub.class_name = %s AND sub.subject_name = m.subject_name
        WHERE m.student_id = %s AND m.exam_id = %s
        """,
        (exam["class_name"], student_id, exam_id),
    )
    marks_list = cursor.fetchall()

    # Class ke andar rank calculate karein
    cursor.execute(
        """
        WITH student_totals AS (
            SELECT m.student_id, COALESCE(SUM(m.marks_obtained), 0) AS total
            FROM marks m
            JOIN students s ON s.id = m.student_id
            WHERE m.exam_id = %s AND s.class_name = %s AND m.is_absent = FALSE
            GROUP BY m.student_id
        )
        SELECT COUNT(*) + 1 AS rank
        FROM student_totals
        WHERE total > COALESCE(
            (SELECT total FROM student_totals WHERE student_id = %s),
            0
        )
        """,
        (exam_id, exam["class_name"], student_id),
    )
    rank_data = cursor.fetchone()
    rank = rank_data["rank"] if rank_data and rank_data["rank"] is not None else 1

    conn.close()

    total_obtained = sum(
        (m["marks_obtained"] or 0) for m in marks_list if not m["is_absent"]
    )
    total_max = sum(
        (m["max_marks"] or 0)
        for m in marks_list
        if not m["is_absent"] and m["max_marks"] is not None
    )
    percentage = (total_obtained / total_max * 100) if total_max > 0 else 0

    if percentage >= 91:
        grade, remark = "A1", "Outstanding! Keep it up."
    elif percentage >= 81:
        grade, remark = "A2", "Excellent performance."
    elif percentage >= 71:
        grade, remark = "B1", "Very Good."
    elif percentage >= 61:
        grade, remark = "B2", "Good, can do better."
    elif percentage >= 51:
        grade, remark = "C1", "Average."
    elif percentage >= 33:
        grade, remark = "C2", "Needs improvement."
    else:
        grade, remark = "E", "Failed. Requires serious attention."

    data = {
        "student": student,
        "exam": exam,
        "marks": marks_list,
        "total_obtained": round(total_obtained, 2),
        "total_max": total_max,
        "percentage": round(percentage, 2),
        "grade": grade,
        "remark": remark,
        "rank": rank,
    }
    return render_template("exams/report_card.html", data=data)
