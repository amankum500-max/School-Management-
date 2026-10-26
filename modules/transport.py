from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort
)
from modules.auth import login_required
from database import (
    create_bus_route, get_bus_routes, get_bus_route,
    update_bus_route, delete_bus_route,
    get_bus_stops, get_bus_stop, create_bus_stop,
    update_bus_stop, delete_bus_stop,
    assign_student_transport, remove_student_transport,
    get_students_on_route, get_student_transport,
    get_all_routes_with_stops, get_student, get_students
)

transport_bp = Blueprint("transport", __name__, url_prefix="/transport")

@transport_bp.route("/")
@login_required
def index():
    search = request.args.get("q", "").strip()
    routes = get_bus_routes(search or None)
    return render_template("transport/index.html",
                           routes=routes, search=search)

# ---------- Routes CRUD ----------
@transport_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("name"):
            flash("Route name zaroori hai", "error")
            return redirect(url_for("transport.add"))
        rid = create_bus_route(data)
        flash("Route create ho gaya", "success")
        return redirect(url_for("transport.view", rid=rid))
    return render_template("transport/form.html", route=None, mode="add")

@transport_bp.route("/<int:rid>")
@login_required
def view(rid):
    r = get_bus_route(rid)
    if not r:
        abort(404)
    stops = get_bus_stops(rid)
    students = get_students_on_route(rid)
    return render_template("transport/view.html",
                           r=r, stops=stops, students=students)

@transport_bp.route("/<int:rid>/edit", methods=["GET", "POST"])
@login_required
def edit(rid):
    r = get_bus_route(rid)
    if not r:
        abort(404)
    if request.method == "POST":
        update_bus_route(rid, request.form.to_dict())
        flash("Route update ho gaya", "success")
        return redirect(url_for("transport.view", rid=rid))
    return render_template("transport/form.html", route=r, mode="edit")

@transport_bp.route("/<int:rid>/delete", methods=["POST"])
@login_required
def remove(rid):
    delete_bus_route(rid)
    flash("Route delete ho gaya", "success")
    return redirect(url_for("transport.index"))

# ---------- Stops ----------
@transport_bp.route("/<int:rid>/stops/add", methods=["POST"])
@login_required
def add_stop(rid):
    data = request.form
    if not data.get("name"):
        flash("Stop name zaroori hai", "error")
        return redirect(url_for("transport.view", rid=rid))
    create_bus_stop(
        rid, data["name"],
        data.get("pickup_time", ""), data.get("drop_time", ""),
        int(data.get("sequence") or 1)
    )
    flash("Stop add ho gaya", "success")
    return redirect(url_for("transport.view", rid=rid))

@transport_bp.route("/stops/<int:sid>/edit", methods=["POST"])
@login_required
def edit_stop(sid):
    s = get_bus_stop(sid)
    if not s:
        abort(404)
    data = request.form
    update_bus_stop(
        sid, data["name"],
        data.get("pickup_time", ""), data.get("drop_time", ""),
        int(data.get("sequence") or 1)
    )
    flash("Stop update ho gaya", "success")
    return redirect(url_for("transport.view", rid=s["route_id"]))

@transport_bp.route("/stops/<int:sid>/delete", methods=["POST"])
@login_required
def remove_stop(sid):
    s = get_bus_stop(sid)
    if not s:
        abort(404)
    delete_bus_stop(sid)
    flash("Stop delete ho gaya", "success")
    return redirect(url_for("transport.view", rid=s["route_id"]))

# ---------- Assign Student ----------
@transport_bp.route("/<int:rid>/students/add", methods=["GET", "POST"])
@login_required
def assign_student(rid):
    r = get_bus_route(rid)
    if not r:
        abort(404)
    stops = get_bus_stops(rid)

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        stop_id = request.form.get("stop_id", type=int)
        if not student_id:
            flash("Student select karo", "error")
            return redirect(url_for("transport.assign_student", rid=rid))
        assign_student_transport(student_id, rid, stop_id)
        flash("Student assign ho gaya", "success")
        return redirect(url_for("transport.view", rid=rid))

    # Search students
    search = request.args.get("q", "").strip()
    students = []
    for s in get_students(search or None):
        # s = (id, name, roll_no, class, section, parent_phone, status)
        students.append({
            "id": s[0], "name": s[1], "roll": s[2],
            "class_name": s[3], "section": s[4],
            "phone": s[5]
        })

    return render_template("transport/assign.html",
                           r=r, stops=stops, students=students,
                           search=search)

@transport_bp.route("/students/<int:student_id>/remove", methods=["POST"])
@login_required
def remove_student(student_id):
    rid = request.form.get("route_id", type=int)
    remove_student_transport(student_id)
    flash("Student transport se remove ho gaya", "success")
    return redirect(url_for("transport.view", rid=rid))
