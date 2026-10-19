import psycopg2
from flask import Blueprint, render_template, request, session, flash, redirect, url_for, jsonify
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


@bp.post("/check-trade")
@login_required("trader")
def check_trade():
    data = request.get_json(silent=True) or {}

    stock_id = data.get("stock_id", "")
    trade_type = data.get("trade_type", "")
    
    try:
        quantity = int(data.get("quantity", 0))
        leverage = float(data.get("leverage_ratio", 1))
    except (ValueError, TypeError):
        return jsonify({"valid": False, "errors": ["Enter a valid quantity and leverage ratio."]})

    if quantity <= 0 or leverage < 1 or trade_type not in ("BUY", "SELL"):
        return jsonify({"valid": False, "errors": ["Enter valid trade details."]})

    warnings = []
    errors = []

    with get_cursor() as cur:
        cur.execute(
            '''SELECT p.portfolio_id, p.cash_balance, p.total_value
               FROM "PORTFOLIO" p
               WHERE p.trader_id = %s''',
            (session["trader_id"],)
        )
        portfolio = cur.fetchone()

        cur.execute(
            '''SELECT stock_id, current_price
               FROM "STOCK"
               WHERE stock_id = %s''',
            (stock_id,)
        )
        stock = cur.fetchone()

        if not portfolio or not stock:
            return jsonify({"valid": False, "errors": ["Portfolio or stock not found."]})

        cur.execute(
            '''SELECT threshold_value
               FROM "RISK_RULE"
               WHERE pattern_type = 'OVER_LEVERAGING'
                 AND is_active = TRUE
               LIMIT 1'''
        )
        leverage_rule = cur.fetchone()

        if leverage_rule and leverage > float(leverage_rule["threshold_value"]):
            warnings.append({
                "type": "OVER_LEVERAGING",
                "message": (
                    f"Leverage {leverage:g} exceeds the configured limit "
                    f"of {float(leverage_rule['threshold_value']):g}."
                )
            })

        if trade_type == "SELL":
            cur.execute(
                '''SELECT quantity
                   FROM "HOLDING"
                   WHERE portfolio_id = %s AND stock_id = %s''',
                (portfolio["portfolio_id"], stock_id)
            )
            holding = cur.fetchone()
            available = holding["quantity"] if holding else 0

            if quantity > available:
                errors.append(
                    f"You have {available} shares available but are trying to sell {quantity}."
                )

        if trade_type == "BUY":
            estimated_cost = quantity * float(stock["current_price"])

            cur.execute(
                '''SELECT margin_enabled
                   FROM "TRADER"
                   WHERE trader_id = %s''',
                (session["trader_id"],)
            )
            trader = cur.fetchone()

            if (
                estimated_cost > float(portfolio["cash_balance"])
                and not (trader and trader["margin_enabled"])
            ):
                errors.append(
                    "Insufficient cash for this purchase, and margin is disabled."
                )

            cur.execute(
                '''SELECT threshold_value
                   FROM "RISK_RULE"
                   WHERE pattern_type = 'CONCENTRATION'
                     AND is_active = TRUE
                   LIMIT 1'''
            )
            concentration_rule = cur.fetchone()

            if concentration_rule:
                cur.execute(
                    '''SELECT quantity, avg_buy_price
                       FROM "HOLDING"
                       WHERE portfolio_id = %s AND stock_id = %s''',
                    (portfolio["portfolio_id"], stock_id)
                )
                holding = cur.fetchone()

                existing_quantity = holding["quantity"] if holding else 0
                projected_value = (
                    (existing_quantity + quantity) * float(stock["current_price"])
                )
                projected_portfolio_value = (
                    float(portfolio["total_value"])
                    + estimated_cost
                )

                if projected_portfolio_value > 0:
                    percentage = (
                        projected_value / projected_portfolio_value
                    ) * 100

                    threshold = float(concentration_rule["threshold_value"])

                    if percentage > threshold:
                        warnings.append({
                            "type": "CONCENTRATION",
                            "message": (
                                f"This purchase would put approximately "
                                f"{percentage:.2f}% of your portfolio in this stock, "
                                f"above the {threshold:g}% threshold."
                            )
                        })

        cur.execute(
            '''SELECT threshold_value
               FROM "RISK_RULE"
               WHERE pattern_type = 'REVENGE_TRADING'
                 AND is_active = TRUE
               LIMIT 1'''
        )
        revenge_rule = cur.fetchone()

        if revenge_rule:
            cur.execute(
                '''SELECT trade_id, trade_timestamp
                   FROM "TRADE"
                   WHERE trader_id = %s
                     AND realized_pnl < 0
                     AND trade_timestamp >=
                         CURRENT_TIMESTAMP
                         - (%s * INTERVAL '1 minute')
                   ORDER BY trade_timestamp DESC
                   LIMIT 1''',
                (
                    session["trader_id"],
                    float(revenge_rule["threshold_value"])
                )
            )
            recent_loss = cur.fetchone()

            if recent_loss:
                warnings.append({
                    "type": "REVENGE_TRADING",
                    "message": (
                        f"You had a realized loss within the last "
                        f"{float(revenge_rule['threshold_value']):g} minutes. "
                        "Consider whether this trade is part of a revenge-trading pattern."
                    )
                })

    return jsonify({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    })


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
            error_message = "Trade could not be completed."

            if isinstance(exc, psycopg2.Error):
                error_message = (
                    getattr(getattr(exc, "diag", None), "message_primary", None)
                    or "Trade could not be completed."
                )

            flash(error_message, "error")
            return redirect(url_for("trader.dashboard"))
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
