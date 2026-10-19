import psycopg2
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from db import get_cursor
from routes.auth import login_required

bp = Blueprint("trader", __name__)

@bp.get("/dashboard")
@login_required("trader")
def dashboard():
    with get_cursor() as cur:
        cur.execute('SELECT * FROM "PORTFOLIO" WHERE trader_id=%s', (session["trader_id"],))
        portfolio = cur.fetchone()
        if not portfolio:
            flash("No portfolio is linked to this trader.", "error")
            return render_template("dashboard.html", portfolio=None, holdings=[])
        cur.execute('''SELECT s.ticker_symbol, h.quantity, h.avg_buy_price,
                              s.current_price, h.quantity*s.current_price AS market_value
                       FROM "HOLDING" h JOIN "STOCK" s ON s.stock_id=h.stock_id
                       WHERE h.portfolio_id=%s ORDER BY s.ticker_symbol''', (portfolio["portfolio_id"],))
        holdings = cur.fetchall()
    return render_template("dashboard.html", portfolio=portfolio, holdings=holdings)

@bp.route("/trade", methods=["GET", "POST"])
@login_required("trader")
def place_trade():
    with get_cursor() as cur:
        if request.method == "GET":
            cur.execute('SELECT stock_id, ticker_symbol, company_name, current_price FROM "STOCK" ORDER BY ticker_symbol')
            return render_template("trade.html", stocks=cur.fetchall())
        try:
            stock_id = request.form.get("stock_id", "")
            trade_type = request.form.get("trade_type", "")
            quantity = int(request.form.get("quantity", "0"))
            leverage = float(request.form.get("leverage_ratio", "1") or 1)
            if trade_type not in ("BUY", "SELL") or quantity <= 0 or leverage < 1:
                flash("Enter valid trade details.", "error")
                cur.execute('SELECT stock_id, ticker_symbol, company_name, current_price FROM "STOCK" ORDER BY ticker_symbol')
                return render_template("trade.html", stocks=cur.fetchall())
            cur.execute('SELECT current_price FROM "STOCK" WHERE stock_id=%s', (stock_id,))
            stock = cur.fetchone()
            if not stock:
                flash("Select a valid stock.", "error")
                return redirect(url_for("trader.place_trade"))
            trade_id = "T" + __import__("uuid").uuid4().hex[:9].upper()
            print("TRADE INSERT VALUES:")
            print("trade_id:", trade_id, len(trade_id))
            print("trader_id:", session["trader_id"], len(session["trader_id"]))
            print("stock_id:", stock_id, len(stock_id))
            print("trade_type:", trade_type, len(trade_type))
            print("quantity:", quantity)
            print("leverage_ratio:", leverage)
            cur.execute('''INSERT INTO "TRADE"
                (trade_id, trader_id, stock_id, trade_type, quantity, price_per_share,
                 leverage_ratio, trade_timestamp, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP,'EXECUTED')
                RETURNING trade_id''',
                (trade_id, session["trader_id"], stock_id, trade_type, quantity, stock["current_price"], leverage))
            cur.execute('SELECT severity, message FROM "BEHAVIORAL_ALERT" WHERE trade_id=%s ORDER BY detected_at DESC', (trade_id,))
            alerts = cur.fetchall()
            for alert in alerts:
                flash(f'[{alert["severity"]}] {alert["message"]}', "warning")
            flash("Trade recorded.", "ok")
        except (ValueError, psycopg2.Error) as exc:
            import traceback
            traceback.print_exc()
            raise
    return redirect(url_for("trader.dashboard"))

@bp.get("/alerts")
@login_required("trader")
def alerts():
    with get_cursor() as cur:
        cur.execute('''SELECT a.alert_id, a.detected_at, a.severity, a.pattern_type,
                              a.message, a.acknowledged, t.trader_id, t.trade_id, s.ticker_symbol
                       FROM "BEHAVIORAL_ALERT" a
                       JOIN "TRADE" t ON t.trade_id=a.trade_id
                       JOIN "STOCK" s ON s.stock_id=t.stock_id
                       WHERE t.trader_id=%s ORDER BY a.detected_at DESC''', (session["trader_id"],))
        rows = cur.fetchall()
    return render_template("alerts.html", alerts=rows)

@bp.post("/alerts/<alert_id>/ack")
@login_required("trader")
def acknowledge_alert(alert_id):
    with get_cursor() as cur:
        cur.execute('''UPDATE "BEHAVIORAL_ALERT" a SET acknowledged=TRUE
                       WHERE a.alert_id=%s AND a.trade_id IN
                       (SELECT trade_id FROM "TRADE" WHERE trader_id=%s)''',
                    (alert_id, session["trader_id"]))
    return redirect(url_for("trader.alerts"))
