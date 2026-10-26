from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    get_timetable_grid, save_timetable_cell,
    get_teacher_timetable, get_staff, get_staff_list,
    get_classes_list, get_students
)

timetable_bp = Blueprint("timetable", __name__, url_prefix="/timetable")

DAYS = [(1, "Mon"), (2, "Tue"), (3, "Wed"), (4, "Thu"), (5, "Fri"), (6, "Sat")]
PERIODS = list(range(1, 9))   # 1..8

@timetable_bp.route("/")
@login_required
def index():
    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    grid = {}
    if class_name:
        grid = get_timetable_grid(class_name, section)

    # unique class-section pairs from students
    combos = set()
    for s in get_students():
        # get_students returns [id,name,roll,class,section,...]
        if s[3]:
            combos.add((s[3], s[4] or ''))
    combos = sorted(combos)

    return render_template(
        "timetable/index.html",
        grid=grid,
        selected_class=class_name,
        selected_section=section,
        combos=combos,
        days=DAYS,
        periods=PERIODS
    )

@timetable_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    class_name = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    if not class_name:
        flash("Class select karo pehle", "error")
        return redirect(url_for("timetable.index"))

    if request.method == "POST":
        saved = 0
        for day in range(1, 7):
            for period in PERIODS:
                subject = request.form.get(f"sub_{day}_{period}", "").strip()
                staff_raw = request.form.get(f"staff_{day}_{period}", "").strip()
                staff_id = int(staff_raw) if staff_raw else None
                save_timetable_cell(class_name, section, day, period, subject, staff_id)
                if subject:
                    saved += 1
        flash(f"Timetable save ho gaya ({saved} slots filled)", "success")
        return redirect(url_for(
            "timetable.index",
            **{"class": class_name, "section": section}
        ))

    grid = get_timetable_grid(class_name, section)
    return render_template(
        "timetable/edit.html",
        class_name=class_name, section=section,
        grid=grid, days=DAYS, periods=PERIODS,
        staff_list=get_staff_list()
    )

@timetable_bp.route("/teacher/<int:staff_id>")
@login_required
def teacher_view(staff_id):
    t = get_staff(staff_id)
    if not t:
        abort(404)

    rows = get_teacher_timetable(staff_id)
    grid = {}
    for r in rows:
        grid[(r[0], r[1])] = {
            "class_name": r[2], "section": r[3] or '', "subject": r[4]
        }
    return render_template(
        "timetable/teacher_view.html",
        teacher=t, grid=grid, days=DAYS, periods=PERIODS
    )
