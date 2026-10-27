import secrets
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session
)
from database import (
    find_user_for_reset, create_password_reset,
    verify_password_otp, consume_password_reset
)
import sms_service

password_reset_bp = Blueprint("password_reset", __name__, url_prefix="/reset")


@password_reset_bp.route("/", methods=["GET", "POST"])
def start():
    if request.method == "POST":
        user_type = request.form.get("user_type", "").strip()
        identifier = request.form.get("identifier", "").strip()

        if user_type not in ("admin", "parent", "teacher") or not identifier:
            flash("Sab fields zaroori hain", "error")
            return redirect(url_for("password_reset.start"))

        user = find_user_for_reset(user_type, identifier)

        # Don't reveal if user exists (security)
        flash("Agar account exist karta hai, OTP bhej diya gaya hai", "success")

        if user:
            phone = user.get("phone")
            if not phone and user_type == "admin":
                # Admin ke paas phone nahi — skip SMS, log
                print(f"[PASSWORD RESET] Admin {user['name']} password reset requested")
                return redirect(url_for("password_reset.start"))

            # Generate 6-digit OTP
            otp = str(secrets.randbelow(900000) + 100000)

            # Send OTP
            res = sms_service.send_sms(
                phone,
                f"Your password reset OTP for school portal: {otp}. Valid 10 min. Do not share. - School"
            )
            if res.get("ok"):
                create_password_reset(user_type, user["id"], phone, otp)
                session["reset_pending"] = {
                    "user_type": user_type,
                    "phone": phone
                }
                return redirect(url_for("password_reset.verify"))
            else:
                flash("OTP send fail — admin se sampark karo", "error")

        return redirect(url_for("password_reset.start"))

    return render_template("password_reset/start.html")


@password_reset_bp.route("/verify", methods=["GET", "POST"])
def verify():
    pending = session.get("reset_pending")
    if not pending:
        flash("Pehle reset start karo", "error")
        return redirect(url_for("password_reset.start"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        result = verify_password_otp(pending["user_type"], pending["phone"], otp)

        if result["ok"]:
            session["reset_verified"] = result["reset_id"]
            return redirect(url_for("password_reset.new_password"))

        flash(result["error"], "error")
        if "attempts_left" in result:
            flash(f"{result['attempts_left']} attempts remaining", "error")

    return render_template("password_reset/verify.html")


@password_reset_bp.route("/new-password", methods=["GET", "POST"])
def new_password():
    reset_id = session.get("reset_verified")
    if not reset_id:
        flash("Pehle OTP verify karo", "error")
        return redirect(url_for("password_reset.start"))

    if request.method == "POST":
        new_pwd = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if len(new_pwd) < 6:
            flash("Kam se kam 6 characters", "error")
        elif new_pwd != confirm:
            flash("Passwords match nahi kar rahe", "error")
        elif consume_password_reset(reset_id, new_pwd):
            session.pop("reset_pending", None)
            session.pop("reset_verified", None)
            flash("Password reset ho gaya! Ab login karo.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Reset fail — dobara try karo", "error")

    return render_template("password_reset/new_password.html")
