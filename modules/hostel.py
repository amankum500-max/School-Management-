from datetime import date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    create_hostel, get_hostels, get_hostel, update_hostel, delete_hostel,
    create_hostel_room, get_hostel_rooms, get_hostel_room, delete_hostel_room,
    allocate_room, checkout_student, get_room_inmates,
    get_hostel_inmates, get_student_hostel, get_hostel_stats,
    get_students, get_student, ROOM_TYPES
)

hostel_bp = Blueprint("hostel", __name__, url_prefix="/hostel")

@hostel_bp.route("/")
@login_required
def index():
    hostels = get_hostels()
    stats = get_hostel_stats()
    return render_template("hostel/index.html",
                           hostels=hostels, stats=stats)

# ---------- Hostels ----------
@hostel_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        if not data.get("name"):
            flash("Name zaroori hai", "error")
            return redirect(url_for("hostel.add"))
        hid = create_hostel(data)
        flash("Hostel create ho gaya", "success")
        return redirect(url_for("hostel.view", hid=hid))
    return render_template("hostel/form.html", h=None, mode="add")

@hostel_bp.route("/<int:hid>")
@login_required
def view(hid):
    h = get_hostel(hid)
    if not h:
        abort(404)
    rooms = get_hostel_rooms(hid)
    inmates = get_hostel_inmates(hid)
    search = request.args.get("q", "").strip()
    if search:
        inmates = get_hostel_inmates(hid, search)
    return render_template("hostel/view.html",
                           h=h, rooms=rooms, inmates=inmates, search=search)

@hostel_bp.route("/<int:hid>/edit", methods=["GET", "POST"])
@login_required
def edit(hid):
    h = get_hostel(hid)
    if not h:
        abort(404)
    if request.method == "POST":
        update_hostel(hid, request.form.to_dict())
        flash("Hostel update ho gaya", "success")
        return redirect(url_for("hostel.view", hid=hid))
    return render_template("hostel/form.html", h=h, mode="edit")

@hostel_bp.route("/<int:hid>/delete", methods=["POST"])
@login_required
def remove(hid):
    delete_hostel(hid)
    flash("Hostel delete ho gaya", "success")
    return redirect(url_for("hostel.index"))

# ---------- Rooms ----------
@hostel_bp.route("/<int:hid>/rooms/add", methods=["POST"])
@login_required
def add_room(hid):
    h = get_hostel(hid)
    if not h:
        abort(404)
    data = request.form.to_dict()
    if not data.get("room_no"):
        flash("Room number zaroori hai", "error")
        return redirect(url_for("hostel.view", hid=hid))
    try:
        create_hostel_room(hid, data)
        flash("Room add ho gaya", "success")
    except Exception:
        flash("Room number already exists", "error")
    return redirect(url_for("hostel.view", hid=hid))

@hostel_bp.route("/rooms/<int:rid>/delete", methods=["POST"])
@login_required
def delete_room(rid):
    room = get_hostel_room(rid)
    if not room:
        abort(404)
    if delete_hostel_room(rid):
        flash("Room delete ho gaya", "success")
    else:
        flash("Room mein active inmates hain — pehle checkout karo", "error")
    return redirect(url_for("hostel.view", hid=room["hostel_id"]))

# ---------- Allocate ----------
@hostel_bp.route("/<int:hid>/allocate", methods=["GET", "POST"])
@login_required
def allocate(hid):
    h = get_hostel(hid)
    if not h:
        abort(404)

    rooms = get_hostel_rooms(hid, only_available=True)

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        room_id = request.form.get("room_id", type=int)
        check_in = request.form.get("check_in") or date.today().isoformat()
        note = request.form.get("note") or ""

        if not student_id or not room_id:
            flash("Student aur room zaroori hain", "error")
            return redirect(url_for("hostel.allocate", hid=hid))

        try:
            allocate_room(student_id, room_id, check_in, note, session["admin_id"])
            flash("Allocation ho gayi", "success")
            return redirect(url_for("hostel.view", hid=hid))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("hostel.allocate", hid=hid))

    # GET — search students
    search = request.args.get("q", "").strip()
    students = []
    for s in get_students(search or None):
        # s = id, name, roll_no, class_name, section, phone, status
        students.append({"id": s[0], "name": s[1], "roll": s[2],
                         "class_name": s[3], "section": s[4]})

    return render_template("hostel/allocate.html",
                           h=h, rooms=rooms, students=students,
                           search=search, today=date.today().isoformat())

@hostel_bp.route("/checkout/<int:student_id>", methods=["POST"])
@login_required
def checkout(student_id):
    hid = request.form.get("hostel_id", type=int)
    if checkout_student(student_id):
        flash("Checkout ho gaya", "success")
    else:
        flash("Koi active allocation nahi mili", "error")
    return redirect(url_for("hostel.view", hid=hid) if hid else url_for("hostel.index"))

@hostel_bp.route("/room/<int:rid>")
@login_required
def room_detail(rid):
    room = get_hostel_room(rid)
    if not room:
        abort(404)
    inmates = get_room_inmates(rid)
    return render_template("hostel/room_detail.html", room=room, inmates=inmates)
