import io
import json
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, Response, jsonify
)
from modules.auth import login_required
from database import (
    backup_all_tables, count_all_rows, restore_table,
    BACKUP_TABLES
)

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")

@backup_bp.route("/")
@login_required
def index():
    counts = count_all_rows()
    return render_template(
        "backup/index.html",
        counts=counts,
        tables=BACKUP_TABLES
    )

@backup_bp.route("/download")
@login_required
def download():
    data = backup_all_tables()
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    filename = f"school_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@backup_bp.route("/download/<table>")
@login_required
def download_table(table):
    if table not in BACKUP_TABLES:
        return redirect(url_for("backup.index"))
    data = backup_all_tables()
    table_data = data["tables"].get(table, {"columns": [], "rows": []})

    import csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = table_data.get("columns", [])
    writer.writerow(cols)
    for r in table_data.get("rows", []):
        writer.writerow([r.get(c, "") for c in cols])

    filename = f"{table}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@backup_bp.route("/restore", methods=["GET", "POST"])
@login_required
def restore():
    if request.method == "POST":
        file = request.files.get("backup_file")
        if not file or not file.filename:
            flash("Backup file select karo", "error")
            return redirect(url_for("backup.restore"))

        if not file.filename.lower().endswith(".json"):
            flash("Sirf .json backup file allowed hai", "error")
            return redirect(url_for("backup.restore"))

        try:
            content = file.read().decode("utf-8")
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            flash(f"Backup file invalid: {str(e)[:100]}", "error")
            return redirect(url_for("backup.restore"))

        if "tables" not in data:
            flash("Ye valid backup file nahi hai", "error")
            return redirect(url_for("backup.restore"))

        # Preview store karo (which tables, how many rows)
        preview = []
        for table in BACKUP_TABLES:
            tdata = data["tables"].get(table, {})
            row_count = len(tdata.get("rows", []))
            if row_count:
                preview.append({"table": table, "count": row_count})

        # Session mein stash
        import flask
        flask.session["restore_preview"] = {
            "tables": data["tables"],
            "summary": preview
        }

        return render_template("backup/restore_preview.html",
                               summary=preview, backup_at=data.get("backup_at"))

    return render_template("backup/restore.html")

@backup_bp.route("/restore/confirm", methods=["POST"])
@login_required
def restore_confirm():
    import flask
    stash = flask.session.get("restore_preview")
    if not stash:
        flash("Restore data nahi mila. Dobara upload karo.", "error")
        return redirect(url_for("backup.restore"))

    all_errors = []
    total_inserted = 0
    table_results = []

    for table in BACKUP_TABLES:
        tdata = stash["tables"].get(table, {})
        rows = tdata.get("rows", [])
        if not rows:
            continue
        inserted, errors = restore_table(table, rows)
        total_inserted += inserted
        table_results.append({
            "table": table, "inserted": inserted,
            "errors": errors[:5], "error_count": len(errors)
        })

    flask.session.pop("restore_preview", None)

    return render_template("backup/restore_result.html",
                           total_inserted=total_inserted,
                           table_results=table_results)

@backup_bp.route("/restore/cancel", methods=["POST"])
@login_required
def restore_cancel():
    import flask
    flask.session.pop("restore_preview", None)
    flash("Restore cancel kar diya", "success")
    return redirect(url_for("backup.restore"))
