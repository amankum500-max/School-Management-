from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from modules.auth import login_required, role_required
from supabase_client import get_conn as get_db_connection
import json

exams_bp = Blueprint("exams", __name__, url_prefix="/exams")


def _row_to_dict(row, keys):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return {k: (row[i] if i < len(row) else None) for i, k in enumerate(keys)}


def _parse_subjects(raw_subjects):
    if not raw_subjects:
        return []
    if isinstance(raw_subjects, list):
        return [str(s).strip() for s in raw_subjects if str(s).strip()]
    if isinstance(raw_subjects, str):
        s = raw_subjects.strip()
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
        return [part.strip() for part in s.split(",") if part.strip()]
    return []


def _calc_grade(pct):
    if pct >= 91:
        return "A1", "Outstanding! Keep it up."
    if pct >= 81:
        return "A2", "Excellent performance."
    if pct >= 71:
        return "B1", "Very Good."
    if pct >= 61:
        return "B2", "Good, can do better."
    if pct >= 51:
        return "C1", "Average."
    if pct >= 33:
        return "C2", "Needs improvement."
    return "E", "Needs serious attention."


# ==========================================
# 1. EXAMS DASHBOARD
# ==========================================
@exams_bp.route("/")
@login_required
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exams ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    exam_keys = ["id", "name", "class_name", "exam_date", "subjects", "max_marks"]
    exams_list = []
    for r in rows:
        d = _row_to_dict(r, exam_keys)
        subs = _parse_subjects(d.get("subjects"))
        d["subjects_list"] = subs
        d["subjects_count"] = len(subs)
        exams_list.append(d)

    return render_template("exams/index.html", exams=exams_list)


@exams_bp.route("/remove/<int:exam_id>", methods=["POST"])
@login_required
def remove(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
    conn.commit()
    conn.close()
    flash("Exam deleted.", "success")
    return redirect(url_for("exams.index"))


@exams_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_exam():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        class_name = (request.form.get("class_name") or "").strip()
        exam_date = (request.form.get("start_date") or request.form.get("exam_date") or "").strip() or None
        subjects_raw = (request.form.get("subjects") or "").strip()
        subjects_list = _parse_subjects(subjects_raw)

        try:
            max_marks = float(request.form.get("max_marks") or 100)
        except (ValueError, TypeError):
            max_marks = 100

        if not name or not class_name:
            conn.close()
            flash("Exam Name aur Class zaroori hai!", "error")
            return redirect(url_for("exams.create_exam"))

        try:
            cursor.execute(
                "INSERT INTO exams (name, class_name, exam_date, subjects, max_marks) VALUES (%s, %s, %s, %s, %s)",
                (name, class_name, exam_date, subjects_list, max_marks),
            )
            conn.commit()
        except Exception:
            conn.rollback()
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
        classes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

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
    exam_raw = cursor.fetchone()
    exam = _row_to_dict(exam_raw, ["id", "name", "class_name", "exam_date", "subjects", "max_marks"])
    if not exam:
        conn.close()
        flash("Exam nahi mila.", "error")
        return redirect(url_for("exams.index"))

    cursor.execute(
        "SELECT id, name, roll_no, class_name, section FROM students WHERE class_name = %s ORDER BY roll_no ASC",
        (exam["class_name"],),
    )
    students = [_row_to_dict(s, ["id", "name", "roll_no", "class_name", "section"]) for s in cursor.fetchall()]

    parsed_subs = _parse_subjects(exam.get("subjects"))
    default_max = exam.get("max_marks") or 100
    subjects = [
        {"id": idx + 1, "class_name": exam["class_name"], "subject_name": sub, "max_marks": default_max}
        for idx, sub in enumerate(parsed_subs)
    ]

    if not subjects:
        try:
            cursor.execute("SELECT id, class_name, subject_name, max_marks FROM subjects WHERE class_name = %s", (exam["class_name"],))
            subjects = [_row_to_dict(sub, ["id", "class_name", "subject_name", "max_marks"]) for sub in cursor.fetchall()]
        except Exception:
            conn.rollback()
            subjects = []

    marks_raw = []
    try:
        cursor.execute("SELECT student_id, subject_name, marks_obtained, is_absent FROM marks WHERE exam_id = %s", (exam_id,))
        marks_raw = cursor.fetchall()
    except Exception:
        conn.rollback()
        cursor.execute("SELECT student_id, subject, obtained, FALSE FROM marks WHERE exam_id = %s", (exam_id,))
        marks_raw = cursor.fetchall()

    conn.close()

    existing_marks = {}
    for m_row in marks_raw:
        m = _row_to_dict(m_row, ["student_id", "subject_name", "marks_obtained", "is_absent"])
        existing_marks[(m["student_id"], m["subject_name"])] = m

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
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    exam_id = data.get("exam_id")
    subject = data.get("subject")
    marks = data.get("marks")
    is_absent = bool(data.get("is_absent", False))

    if not student_id or not exam_id or not subject:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if marks == "" or marks is None or is_absent:
        marks = 0.0
    else:
        try:
            marks = float(marks)
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Invalid marks value"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM marks WHERE student_id = %s AND exam_id = %s AND subject_name = %s",
            (student_id, exam_id, subject),
        )
        existing = cursor.fetchone()
        if existing:
            existing_id = existing["id"] if isinstance(existing, dict) else existing[0]
            cursor.execute(
                "UPDATE marks SET marks_obtained = %s, is_absent = %s WHERE id = %s",
                (marks, is_absent, existing_id),
            )
        else:
            cursor.execute(
                "INSERT INTO marks (student_id, exam_id, subject_name, marks_obtained, is_absent) VALUES (%s, %s, %s, %s, %s)",
                (student_id, exam_id, subject, marks, is_absent),
            )
    except Exception:
        conn.rollback()
        cursor.execute(
            "SELECT id FROM marks WHERE student_id = %s AND exam_id = %s AND subject = %s",
            (student_id, exam_id, subject),
        )
        existing = cursor.fetchone()
        if existing:
            existing_id = existing["id"] if isinstance(existing, dict) else existing[0]
            cursor.execute("UPDATE marks SET obtained = %s WHERE id = %s", (marks, existing_id))
        else:
            cursor.execute(
                "INSERT INTO marks (student_id, exam_id, subject, obtained) VALUES (%s, %s, %s, %s)",
                (student_id, exam_id, subject, marks),
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
    exam_raw = cursor.fetchone()
    exam = _row_to_dict(exam_raw, ["id", "name", "class_name", "exam_date", "subjects", "max_marks"])
    if not exam:
        conn.close()
        flash("Exam nahi mila.", "error")
        return redirect(url_for("exams.index"))

    subs = _parse_subjects(exam.get("subjects"))
    per_sub_max = float(exam.get("max_marks") or 100)
    total_max = per_sub_max * len(subs) if subs else per_sub_max

    try:
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
        merit_raw = cursor.fetchall()
    except Exception:
        conn.rollback()
        cursor.execute(
            """
            SELECT s.id, s.name, s.roll_no, COALESCE(SUM(m.obtained), 0) AS total_obtained
            FROM students s
            JOIN marks m ON s.id = m.student_id
            WHERE m.exam_id = %s AND s.class_name = %s
            GROUP BY s.id, s.name, s.roll_no
            ORDER BY total_obtained DESC, s.roll_no ASC
            """,
            (exam_id, exam["class_name"]),
        )
        merit_raw = cursor.fetchall()

    conn.close()

    merit_list = []
    for idx, r in enumerate(merit_raw, start=1):
        item = _row_to_dict(r, ["id", "name", "roll_no", "total_obtained"])
        obt = float(item.get("total_obtained") or 0)
        pct = round((obt / total_max * 100), 2) if total_max > 0 else 0.0
        grd, _ = _calc_grade(pct)
        item["total_max"] = total_max
        item["percentage"] = pct
        item["grade"] = grd
        item["rank"] = idx
        merit_list.append(item)

    return render_template("exams/merit.html", exam=exam, merit_list=merit_list)


# ==========================================
# 4. ULTIMATE REPORT CARD (A4 Print Ready)
# ==========================================
@exams_bp.route("/report-card/<int:student_id>/<int:exam_id>")
@login_required
def report_card(student_id, exam_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, roll_no, class_name, section FROM students WHERE id = %s", (student_id,))
    student = _row_to_dict(cursor.fetchone(), ["id", "name", "roll_no", "class_name", "section"])

    cursor.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
    exam = _row_to_dict(cursor.fetchone(), ["id", "name", "class_name", "exam_date", "subjects", "max_marks"])

    if not student or not exam:
        conn.close()
        flash("Record not found", "error")
        return redirect(url_for("exams.index"))

    default_max = float(exam.get("max_marks") or 100)
    marks_list = []
    try:
        cursor.execute(
            """
            SELECT m.subject_name, m.marks_obtained, m.is_absent, COALESCE(sub.max_marks, %s)
            FROM marks m
            LEFT JOIN subjects sub
                ON sub.class_name = %s AND sub.subject_name = m.subject_name
            WHERE m.student_id = %s AND m.exam_id = %s
            """,
            (default_max, exam["class_name"], student_id, exam_id),
        )
        marks_list = [_row_to_dict(m, ["subject_name", "marks_obtained", "is_absent", "max_marks"]) for m in cursor.fetchall()]
    except Exception:
        conn.rollback()
        cursor.execute(
            "SELECT subject, obtained, FALSE, %s FROM marks WHERE student_id = %s AND exam_id = %s",
            (default_max, student_id, exam_id),
        )
        marks_list = [_row_to_dict(m, ["subject_name", "marks_obtained", "is_absent", "max_marks"]) for m in cursor.fetchall()]

    conn.close()

    total_obtained = sum((m["marks_obtained"] or 0) for m in marks_list if not m.get("is_absent"))
    total_max = sum((m["max_marks"] or default_max) for m in marks_list if not m.get("is_absent"))
    percentage = (total_obtained / total_max * 100) if total_max > 0 else 0.0
    grade, remark = _calc_grade(percentage)

    data = {
        "student": student,
        "exam": exam,
        "marks": marks_list,
        "total_obtained": round(total_obtained, 2),
        "total_max": total_max,
        "percentage": round(percentage, 2),
        "grade": grade,
        "remark": remark,
        "rank": 1,
    }
    return render_template("exams/report_card.html", data=data)
