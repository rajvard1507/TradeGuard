from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_cursor

bp = Blueprint("auth", __name__)

def login_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                return redirect(url_for("auth.login"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_cursor() as cur:
            cur.execute('SELECT user_id, name, email, password_hash FROM "USER" WHERE lower(email)=lower(%s)', (email,))
            user = cur.fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "error")
                return render_template("login.html")
            cur.execute('SELECT trader_id FROM "TRADER" WHERE user_id=%s', (user["user_id"],))
            trader = cur.fetchone()
            cur.execute('SELECT admin_id FROM "ADMIN" WHERE user_id=%s', (user["user_id"],))
            admin = cur.fetchone()
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
        flash("This account has no trader or admin role.", "error")
    return render_template("login.html")

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter a name, email, and password with at least 8 characters.", "error")
            return render_template("register.html")
        password_hash = generate_password_hash(password)
        with get_cursor() as cur:
            cur.execute('SELECT 1 FROM "USER" WHERE lower(email)=lower(%s)', (email,))
            if cur.fetchone():
                flash("An account with that email already exists.", "error")
                return render_template("register.html")
            cur.execute('INSERT INTO "USER" (user_id, name, email, password_hash, created_at) VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP) RETURNING user_id', ("USR-" + __import__("uuid").uuid4().hex, name, email, password_hash))
            user_id = cur.fetchone()["user_id"]
            trader_id = "TRD-" + __import__("uuid").uuid4().hex
            portfolio_id = "PFL-" + __import__("uuid").uuid4().hex
            cur.execute('INSERT INTO "TRADER" (trader_id, user_id, account_balance, margin_enabled, kyc_verified) VALUES (%s,%s,%s,FALSE,FALSE)', (trader_id, user_id, 10000))
            cur.execute('INSERT INTO "PORTFOLIO" (portfolio_id, trader_id, cash_balance, total_value, last_updated) VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP)', (portfolio_id, trader_id, 10000, 10000))
        flash("Registration successful. Please log in.", "ok")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
