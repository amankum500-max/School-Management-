from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    create_event, get_events, get_event, update_event,
    delete_event, get_events_for_month_grid, EVENT_TYPES,
    get_classes_list
)

events_bp = Blueprint("events", __name__, url_prefix="/events")

@events_bp.route("/")
@login_required
def index():
    event_type = request.args.get("type", "").strip()
    month = request.args.get("month", "").strip()
    view = request.args.get("view", "upcoming")   # upcoming | all | month

    if view == "month" and not month:
        month = datetime.now().strftime("%Y-%m")

    items = get_events(
        month=month if view == "month" else None,
        event_type=event_type or None,
        upcoming_only=(view == "upcoming")
    )

    return render_template(
        "events/index.html",
        items=items, event_types=EVENT_TYPES,
        selected_type=event_type, month=month, view=view,
        today=date.today()
    )

@events_bp.route("/calendar")
@login_required
def calendar_view():
    month_str = request.args.get("month", "").strip()
    if month_str:
        try:
            y, m = map(int, month_str.split("-"))
        except ValueError:
            y, m = datetime.now().year, datetime.now().month
    else:
        y, m = datetime.now().year, datetime.now().month

    grid = get_events_for_month_grid(y, m)

    # Build month grid
    import calendar as _cal
    cal = _cal.Calendar(firstweekday=0)     # Monday start
    weeks = cal.monthdatescalendar(y, m)

    # Prev/next month
    prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    next_y, next_m = (y + 1, 1) if m == 12 else (y, m + 1)

    return render_template(
        "events/calendar.html",
        weeks=weeks, year=y, month=m, grid=grid,
        month_name=_cal.month_name[m],
        prev_str=f"{prev_y}-{prev_m:02d}",
        next_str=f"{next_y}-{next_m:02d}",
        today=date.today()
    )

@events_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("title") or not data.get("start_date"):
            flash("Title aur start date zaroori hain", "error")
            return redirect(url_for("events.add"))
        eid = create_event(data, session["admin_id"])
        flash("Event create ho gaya", "success")
        return redirect(url_for("events.view", eid=eid))

    return render_template("events/form.html",
                           event=None, mode="add",
                           event_types=EVENT_TYPES,
                           classes=get_classes_list(),
                           today=datetime.now().strftime("%Y-%m-%d"))

@events_bp.route("/<int:eid>")
@login_required
def view(eid):
    e = get_event(eid)
    if not e:
        abort(404)
    return render_template("events/view.html", e=e, today=date.today())

@events_bp.route("/<int:eid>/edit", methods=["GET", "POST"])
@login_required
def edit(eid):
    e = get_event(eid)
    if not e:
        abort(404)
    if request.method == "POST":
        update_event(eid, request.form.to_dict())
        flash("Event update ho gaya", "success")
        return redirect(url_for("events.view", eid=eid))
    return render_template("events/form.html",
                           event=e, mode="edit",
                           event_types=EVENT_TYPES,
                           classes=get_classes_list(),
                           today=e["start_date"])

@events_bp.route("/<int:eid>/delete", methods=["POST"])
@login_required
def remove(eid):
    delete_event(eid)
    flash("Event delete ho gaya", "success")
    return redirect(url_for("events.index"))
