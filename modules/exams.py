@exams_bp.route("/")
@login_required
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ✅ FIX: SELECT * ki jagah exact columns likhein
    cursor.execute("SELECT id, name, class_name, exam_date, subjects, max_marks FROM exams ORDER BY id DESC")
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
