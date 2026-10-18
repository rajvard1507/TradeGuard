CREATE OR REPLACE VIEW v_trader_alerts AS
SELECT
    a.alert_id,
    a.detected_at,
    a.severity,
    a.pattern_type,
    a.message,
    a.acknowledged,
    t.trader_id,
    t.trade_id,
    s.ticker_symbol,
    t.trade_type,
    t.quantity,
    t.price_per_share
FROM "BEHAVIORAL_ALERT" a
JOIN "TRADE" t
    ON t.trade_id = a.trade_id
JOIN "STOCK" s
    ON s.stock_id = t.stock_id;


CREATE OR REPLACE VIEW v_portfolio_summary AS
SELECT
    p.portfolio_id,
    p.trader_id,
    p.cash_balance,
    p.total_value,
    COUNT(h.stock_id) AS number_of_holdings,
    COALESCE(
        SUM(h.quantity * s.current_price),
        0
    ) AS holdings_market_value
FROM "PORTFOLIO" p
LEFT JOIN "HOLDING" h
    ON h.portfolio_id = p.portfolio_id
LEFT JOIN "STOCK" s
    ON s.stock_id = h.stock_id
GROUP BY
    p.portfolio_id,
    p.trader_id,
    p.cash_balance,
    p.total_value;


CREATE OR REPLACE VIEW v_admin_queue AS
SELECT
    a.alert_id,
    a.detected_at,
    a.severity,
    a.pattern_type,
    a.message,
    a.acknowledged,
    t.trader_id,
    u.name AS trader_name,
    s.ticker_symbol,
    t.trade_type,
    t.quantity,
    t.price_per_share,
    r.rule_id,
    r.threshold_value,
    ar.review_id,
    ar.action_taken,
    ar.notes,
    ar.reviewed_at
FROM "BEHAVIORAL_ALERT" a
JOIN "TRADE" t
    ON t.trade_id = a.trade_id
JOIN "TRADER" tr
    ON tr.trader_id = t.trader_id
JOIN "USER" u
    ON u.user_id = tr.user_id
JOIN "STOCK" s
    ON s.stock_id = t.stock_id
JOIN "RISK_RULE" r
    ON r.rule_id = a.rule_id
LEFT JOIN "ADMIN_REVIEW" ar
    ON ar.alert_id = a.alert_id;