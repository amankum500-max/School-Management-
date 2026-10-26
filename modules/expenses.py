from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, abort
)
from modules.auth import login_required
from database import (
    create_expense, get_expenses, get_expense, update_expense,
    delete_expense, get_expense_summary, get_pnl,
    get_expense_monthly_trend, EXPENSE_CATEGORIES
)

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

@expenses_bp.route("/")
@login_required
def index():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()

    items = get_expenses(month, category or None, search or None)
    summary = get_expense_summary(month)

    return render_template(
        "expenses/index.html",
        month=month, items=items, summary=summary,
        categories=EXPENSE_CATEGORIES,
        selected_category=category, search=search
    )

@expenses_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data = request.form.to_dict()
        try:
            if not data.get("category") or not data.get("amount"):
                raise ValueError("Category aur amount zaroori hain")
            create_expense(data, session["admin_id"])
            flash("Expense record ho gaya", "success")
            return redirect(url_for("expenses.index"))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return redirect(url_for("expenses.add"))
    return render_template("expenses/form.html",
                           expense=None, mode="add",
                           categories=EXPENSE_CATEGORIES,
                           today=datetime.now().strftime("%Y-%m-%d"))

@expenses_bp.route("/<int:eid>/edit", methods=["GET", "POST"])
@login_required
def edit(eid):
    e = get_expense(eid)
    if not e:
        abort(404)
    if request.method == "POST":
        update_expense(eid, request.form.to_dict())
        flash("Expense update ho gaya", "success")
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html",
                           expense=e, mode="edit",
                           categories=EXPENSE_CATEGORIES,
                           today=e["expense_date"])

@expenses_bp.route("/<int:eid>/delete", methods=["POST"])
@login_required
def remove(eid):
    delete_expense(eid)
    flash("Expense delete ho gaya", "success")
    return redirect(url_for("expenses.index"))

@expenses_bp.route("/pnl")
@login_required
def pnl():
    month = request.args.get("month") or datetime.now().strftime("%Y-%m")
    data = get_pnl(month)
    trend = get_expense_monthly_trend(6)
    return render_template("expenses/pnl.html",
                           p=data, trend=trend, month=month)
