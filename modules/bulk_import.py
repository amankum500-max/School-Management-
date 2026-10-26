import io
import csv
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, Response, session
)
from modules.auth import login_required
from database import (
    get_existing_roll_nos, bulk_create_students
)

bulk_bp = Blueprint("bulk", __name__, url_prefix="/students/bulk")

REQUIRED_FIELDS = ["name"]
ALL_FIELDS = [
    "name", "roll_no", "class_name", "section", "gender", "dob",
    "parent_name", "parent_phone", "address", "admission_date"
]

def _validate_row(raw):
    """Ek CSV row ko validate karo. Returns (data_dict, error_or_none)"""
    d = {k: (raw.get(k) or "").strip() for k in ALL_FIELDS}

    # name required
    if not d["name"]:
        return d, "Name khaali hai"

    # phone format
    if d["parent_phone"]:
        phone_digits = "".join(ch for ch in d["parent_phone"] if ch.isdigit())
        if len(phone_digits) < 10 or len(phone_digits) > 15:
            return d, f"Phone galat ({d['parent_phone']}) — 10-15 digits chahiye"
        d["parent_phone"] = phone_digits

    # dob parse
    if d["dob"]:
        try:
            datetime.strptime(d["dob"], "%Y-%m-%d")
        except ValueError:
            return d, f"DOB format galat ({d['dob']}) — YYYY-MM-DD chahiye"

    # admission_date parse
    if d["admission_date"]:
        try:
            datetime.strptime(d["admission_date"], "%Y-%m-%d")
        except ValueError:
            d["admission_date"] = ""

    # gender normalize
    if d["gender"]:
        g = d["gender"].lower()
        if g in ("m", "male", "boy"):
            d["gender"] = "Male"
        elif g in ("f", "female", "girl"):
            d["gender"] = "Female"
        else:
            d["gender"] = "Other"

    return d, None

@bulk_bp.route("/", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or not file.filename:
            flash("CSV file select karo", "error")
            return redirect(url_for("bulk.upload"))

        if not file.filename.lower().endswith(".csv"):
            flash("Sirf .csv file allowed hai", "error")
            return redirect(url_for("bulk.upload"))

        try:
            content = file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = file.read().decode("latin-1")
            except Exception:
                flash("File read nahi ho payi. UTF-8 CSV use karo.", "error")
                return redirect(url_for("bulk.upload"))

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            flash("CSV khaali hai ya header row nahi hai", "error")
            return redirect(url_for("bulk.upload"))

        headers = [h.strip().lower() for h in reader.fieldnames]
        if "name" not in headers:
            flash("CSV mein 'name' column zaroori hai. Template download karo.", "error")
            return redirect(url_for("bulk.upload"))

        raw_rows = []
        for row in reader:
            cleaned = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            raw_rows.append(cleaned)

        if not raw_rows:
            flash("CSV mein koi data row nahi hai", "error")
            return redirect(url_for("bulk.upload"))

        # Validate + collect roll_nos for duplicate check
        validated = []
        roll_nos_in_file = [r.get("roll_no", "") for r in raw_rows if r.get("roll_no")]
        existing_rolls = get_existing_roll_nos(roll_nos_in_file)

        seen_rolls = set()
        for idx, r in enumerate(raw_rows):
            d, err = _validate_row(r)
            if not err and d.get("roll_no"):
                if d["roll_no"] in seen_rolls:
                    err = f"Duplicate roll_no file mein ({d['roll_no']})"
                elif d["roll_no"] in existing_rolls:
                    err = f"Roll_no database mein already hai ({d['roll_no']})"
                else:
                    seen_rolls.add(d["roll_no"])

            validated.append({
                "row_num": idx + 2,   # +2 kyunki header row 1 hai
                "data": d,
                "error": err
            })

        # Stash in session for confirm step
        valid_count = sum(1 for v in validated if not v["error"])
        error_count = len(validated) - valid_count

        session["bulk_preview"] = [
            {"row_num": v["row_num"], "data": v["data"], "error": v["error"]}
            for v in validated
        ]

        return render_template(
            "bulk/preview.html",
            rows=validated,
            valid_count=valid_count,
            error_count=error_count,
            total=len(validated)
        )

    return render_template("bulk/upload.html")

@bulk_bp.route("/confirm", methods=["POST"])
@login_required
def confirm():
    stash = session.get("bulk_preview")
    if not stash:
        flash("Koi upload nahi mila. Dobara upload karo.", "error")
        return redirect(url_for("bulk.upload"))

    valid_rows = [item["data"] for item in stash if not item["error"]]
    if not valid_rows:
        flash("Koi valid row nahi hai insert ke liye", "error")
        return redirect(url_for("bulk.upload"))

    inserted, failed = bulk_create_students(valid_rows)
    session.pop("bulk_preview", None)

    return render_template(
        "bulk/result.html",
        inserted=inserted,
        failed=failed,
        total=len(valid_rows)
    )

@bulk_bp.route("/cancel", methods=["POST"])
@login_required
def cancel():
    session.pop("bulk_preview", None)
    flash("Import cancel kar diya", "success")
    return redirect(url_for("bulk.upload"))

@bulk_bp.route("/template")
def download_template():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(ALL_FIELDS)
    # Sample row
    writer.writerow([
        "Rahul Sharma", "101", "5", "A", "Male", "2014-05-15",
        "Vijay Sharma", "9876543210", "123 MG Road, Delhi", "2024-04-01"
    ])
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_template.csv"}
    )
