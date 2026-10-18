CREATE OR REPLACE VIEW v_trader_alerts AS
SELECT a.alert_id, a.detected_at, a.severity, a.pattern_type, a.message, a.acknowledged,
       t.trader_id, t.trade_id, s.ticker_symbol
FROM "BEHAVIORAL_ALERT" a
JOIN "TRADE" t ON t.trade_id = a.trade_id
JOIN "STOCK" s ON s.stock_id = t.stock_id;

CREATE OR REPLACE VIEW v_admin_queue AS
SELECT a.alert_id, a.detected_at, a.severity, a.pattern_type, a.message, a.acknowledged,
       u.name AS trader_name, s.ticker_symbol, rr.rule_id, rr.threshold_value,
       ar.review_id, ar.notes, ar.action_taken
FROM "BEHAVIORAL_ALERT" a
JOIN "TRADE" t ON t.trade_id = a.trade_id
JOIN "TRADER" tr ON tr.trader_id = t.trader_id
JOIN "USER" u ON u.user_id = tr.user_id
JOIN "STOCK" s ON s.stock_id = t.stock_id
JOIN "RISK_RULE" rr ON rr.rule_id = a.rule_id
LEFT JOIN "ADMIN_REVIEW" ar ON ar.alert_id = a.alert_id;
