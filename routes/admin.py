from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_cursor
from routes.auth import login_required

bp = Blueprint("admin", __name__)

@bp.get("/queue")
@login_required("admin")
def queue():
    with get_cursor() as cur:
        cur.execute('''SELECT a.alert_id, a.detected_at, a.severity, a.pattern_type, a.message,
                              a.acknowledged, u.name AS trader_name, s.ticker_symbol,
                              rr.rule_id, rr.threshold_value, ar.review_id, ar.notes, ar.action_taken
                       FROM "BEHAVIORAL_ALERT" a
                       JOIN "TRADE" t ON t.trade_id=a.trade_id
                       JOIN "TRADER" tr ON tr.trader_id=t.trader_id
                       JOIN "USER" u ON u.user_id=tr.user_id
                       JOIN "STOCK" s ON s.stock_id=t.stock_id
                       JOIN "RISK_RULE" rr ON rr.rule_id=a.rule_id
                       LEFT JOIN "ADMIN_REVIEW" ar ON ar.alert_id=a.alert_id
                       ORDER BY a.detected_at DESC''')
        alerts = cur.fetchall()
    return render_template("admin_queue.html", alerts=alerts)

@bp.route("/review/<alert_id>", methods=["GET", "POST"])
@login_required("admin")
def review(alert_id):
    if request.method == "POST":
        notes = request.form.get("notes", "").strip()
        action_taken = request.form.get("action_taken", "").strip()
        with get_cursor() as cur:
            cur.execute('''INSERT INTO "ADMIN_REVIEW"
                           (review_id, admin_id, alert_id, notes, action_taken, reviewed_at)
                           VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
                           ON CONFLICT (alert_id) DO UPDATE SET
                             admin_id=EXCLUDED.admin_id,
                             notes=EXCLUDED.notes,
                             action_taken=EXCLUDED.action_taken,
                             reviewed_at=EXCLUDED.reviewed_at''',
                        ("R" + __import__("uuid").uuid4().hex[:9].upper(), session["admin_id"], alert_id, notes, action_taken))
        flash("Review saved.", "ok")
        return redirect(url_for("admin.queue"))
    with get_cursor() as cur:
        cur.execute('SELECT alert_id, pattern_type, severity, message FROM "BEHAVIORAL_ALERT" WHERE alert_id=%s', (alert_id,))
        alert = cur.fetchone()
    if not alert:
        flash("Alert not found.", "error")
        return redirect(url_for("admin.queue"))
    return render_template("admin_review.html", alert=alert)
