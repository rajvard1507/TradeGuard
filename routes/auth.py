import uuid
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_cursor

bp = Blueprint("auth", __name__)


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login"))

            if role and session.get("role") != role:
                flash("You are not authorized to access this page.", "error")
                return redirect(url_for("auth.login"))

            return view(*args, **kwargs)

        return wrapped

    return decorator


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        with get_cursor() as cursor:
            cursor.execute(
                'SELECT user_id, name, email, password_hash FROM "USER" WHERE LOWER(email) = LOWER(%s)',
                (email,)
            )
            user = cursor.fetchone()

            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "error")
                return render_template("login.html")

            cursor.execute(
                'SELECT trader_id FROM "TRADER" WHERE user_id = %s',
                (user["user_id"],)
            )
            trader = cursor.fetchone()

            cursor.execute(
                'SELECT admin_id FROM "ADMIN" WHERE user_id = %s',
                (user["user_id"],)
            )
            admin = cursor.fetchone()

        session.clear()
        session["user_id"] = user["user_id"]
        session["name"] = user["name"]

        if admin:
            session["role"] = "admin"
            session["admin_id"] = admin["admin_id"]
            return redirect(url_for("admin.queue"))

        if trader:
            session["role"] = "trader"
            session["trader_id"] = trader["trader_id"]
            return redirect(url_for("trader.dashboard"))

        session.clear()
        flash("Your account has no assigned application role.", "error")

    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        user_id = "USR-" + uuid.uuid4().hex
        trader_id = "TRD-" + uuid.uuid4().hex
        portfolio_id = "PFL-" + uuid.uuid4().hex

        with get_cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM "USER" WHERE LOWER(email) = LOWER(%s)',
                (email,)
            )

            if cursor.fetchone():
                flash("An account with this email already exists.", "error")
                return render_template("register.html")

            cursor.execute(
                '''INSERT INTO "USER"
                   (user_id, name, email, password_hash, created_at)
                   VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)''',
                (user_id, name, email, password_hash)
            )

            cursor.execute(
                '''INSERT INTO "TRADER"
                   (trader_id, user_id, account_balance, margin_enabled, kyc_verified)
                   VALUES (%s, %s, %s, FALSE, FALSE)''',
                (trader_id, user_id, 10000)
            )

            cursor.execute(
                '''INSERT INTO "PORTFOLIO"
                   (portfolio_id, trader_id, cash_balance, total_value, last_updated)
                   VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)''',
                (portfolio_id, trader_id, 10000, 10000)
            )

        flash("Registration successful. You can now log in.", "ok")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))