CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION fn_prepare_trade()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_id VARCHAR;
    v_cash NUMERIC;
    v_margin BOOLEAN;
    v_quantity INTEGER;
    v_avg_price NUMERIC;
BEGIN
    SELECT p.portfolio_id, p.cash_balance, t.margin_enabled
    INTO v_portfolio_id, v_cash, v_margin
    FROM "PORTFOLIO" p
    JOIN "TRADER" t ON t.trader_id = p.trader_id
    WHERE p.trader_id = NEW.trader_id
    FOR UPDATE OF p;

    IF v_portfolio_id IS NULL THEN
        RAISE EXCEPTION 'Portfolio not found for trader';
    END IF;

    IF NEW.quantity <= 0 OR NEW.price_per_share <= 0 THEN
        RAISE EXCEPTION 'Quantity and price must be positive';
    END IF;

    IF NEW.trade_type = 'BUY' THEN
        IF v_cash < NEW.quantity * NEW.price_per_share
           AND NOT COALESCE(v_margin, FALSE) THEN
            RAISE EXCEPTION 'Insufficient cash and margin is disabled';
        END IF;

        NEW.realized_pnl := NULL;

    ELSIF NEW.trade_type = 'SELL' THEN
        SELECT quantity, avg_buy_price
        INTO v_quantity, v_avg_price
        FROM "HOLDING"
        WHERE portfolio_id = v_portfolio_id
          AND stock_id = NEW.stock_id
        FOR UPDATE;

        IF v_quantity IS NULL OR v_quantity < NEW.quantity THEN
            RAISE EXCEPTION 'Insufficient holdings';
        END IF;

        NEW.realized_pnl :=
            (NEW.price_per_share - v_avg_price) * NEW.quantity;

    ELSE
        RAISE EXCEPTION 'Invalid trade type';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_10_prepare ON "TRADE";

CREATE TRIGGER trg_10_prepare
BEFORE INSERT ON "TRADE"
FOR EACH ROW
EXECUTE FUNCTION fn_prepare_trade();


CREATE OR REPLACE FUNCTION fn_apply_trade()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_id VARCHAR;
BEGIN
    SELECT portfolio_id
    INTO v_portfolio_id
    FROM "PORTFOLIO"
    WHERE trader_id = NEW.trader_id
    FOR UPDATE;

    IF NEW.trade_type = 'BUY' THEN

        INSERT INTO "HOLDING"
            (portfolio_id, stock_id, quantity, avg_buy_price)
        VALUES
            (v_portfolio_id, NEW.stock_id, NEW.quantity, NEW.price_per_share)

        ON CONFLICT (portfolio_id, stock_id)
        DO UPDATE SET
            avg_buy_price =
                (
                    "HOLDING".quantity * "HOLDING".avg_buy_price
                    + EXCLUDED.quantity * EXCLUDED.avg_buy_price
                )
                / ("HOLDING".quantity + EXCLUDED.quantity),

            quantity = "HOLDING".quantity + EXCLUDED.quantity;

        UPDATE "PORTFOLIO"
        SET cash_balance =
            cash_balance - NEW.quantity * NEW.price_per_share
        WHERE portfolio_id = v_portfolio_id;

    ELSE

        UPDATE "HOLDING"
        SET quantity = quantity - NEW.quantity
        WHERE portfolio_id = v_portfolio_id
          AND stock_id = NEW.stock_id;

        DELETE FROM "HOLDING"
        WHERE portfolio_id = v_portfolio_id
          AND stock_id = NEW.stock_id
          AND quantity = 0;

        UPDATE "PORTFOLIO"
        SET cash_balance =
            cash_balance + NEW.quantity * NEW.price_per_share
        WHERE portfolio_id = v_portfolio_id;

    END IF;

    UPDATE "PORTFOLIO" p
    SET total_value =
        p.cash_balance + COALESCE(
            (
                SELECT SUM(h.quantity * s.current_price)
                FROM "HOLDING" h
                JOIN "STOCK" s ON s.stock_id = h.stock_id
                WHERE h.portfolio_id = v_portfolio_id
            ),
            0
        ),
        last_updated = CURRENT_TIMESTAMP
    WHERE p.portfolio_id = v_portfolio_id;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_20_apply ON "TRADE";

CREATE TRIGGER trg_20_apply
AFTER INSERT ON "TRADE"
FOR EACH ROW
EXECUTE FUNCTION fn_apply_trade();


CREATE OR REPLACE FUNCTION fn_check_revenge()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    r RECORD;
    previous_trade RECORD;
BEGIN
    SELECT *
    INTO r
    FROM "RISK_RULE"
    WHERE pattern_type = 'REVENGE_TRADING'
      AND is_active = TRUE
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    SELECT trade_id, realized_pnl
    INTO previous_trade
    FROM "TRADE"
    WHERE trader_id = NEW.trader_id
      AND trade_id <> NEW.trade_id
      AND realized_pnl < 0
      AND trade_timestamp >=
          NEW.trade_timestamp
          - make_interval(mins => r.threshold_value::INTEGER)
    ORDER BY trade_timestamp DESC
    LIMIT 1;

    IF FOUND THEN
        INSERT INTO "BEHAVIORAL_ALERT"
            (
                alert_id, trade_id, rule_id, pattern_type,
                severity, message, detected_at, acknowledged
            )
        VALUES
            (
                'ALT-' || gen_random_uuid()::TEXT,
                NEW.trade_id,
                r.rule_id,
                r.pattern_type,
                'HIGH',
                format(
                    'Trade placed within %s minutes of a realized loss.',
                    r.threshold_value
                ),
                CURRENT_TIMESTAMP,
                FALSE
            );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_30_revenge ON "TRADE";

CREATE TRIGGER trg_30_revenge
AFTER INSERT ON "TRADE"
FOR EACH ROW
EXECUTE FUNCTION fn_check_revenge();


CREATE OR REPLACE FUNCTION fn_check_leverage()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    r RECORD;
BEGIN
    SELECT *
    INTO r
    FROM "RISK_RULE"
    WHERE pattern_type = 'OVER_LEVERAGING'
      AND is_active = TRUE
    LIMIT 1;

    IF FOUND AND NEW.leverage_ratio > r.threshold_value THEN

        INSERT INTO "BEHAVIORAL_ALERT"
            (
                alert_id, trade_id, rule_id, pattern_type,
                severity, message, detected_at, acknowledged
            )
        VALUES
            (
                'ALT-' || gen_random_uuid()::TEXT,
                NEW.trade_id,
                r.rule_id,
                r.pattern_type,
                'MEDIUM',
                format(
                    'Leverage ratio %s exceeds the limit of %s.',
                    NEW.leverage_ratio,
                    r.threshold_value
                ),
                CURRENT_TIMESTAMP,
                FALSE
            );

    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_40_leverage ON "TRADE";

CREATE TRIGGER trg_40_leverage
AFTER INSERT ON "TRADE"
FOR EACH ROW
EXECUTE FUNCTION fn_check_leverage();


CREATE OR REPLACE FUNCTION fn_check_concentration()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    r RECORD;
    v_percentage NUMERIC;
    v_portfolio_id VARCHAR;
BEGIN
    IF NEW.trade_type <> 'BUY' THEN
        RETURN NEW;
    END IF;

    SELECT *
    INTO r
    FROM "RISK_RULE"
    WHERE pattern_type = 'CONCENTRATION'
      AND is_active = TRUE
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    SELECT portfolio_id
    INTO v_portfolio_id
    FROM "PORTFOLIO"
    WHERE trader_id = NEW.trader_id;

    SELECT
        100.0 * h.quantity * s.current_price
        / NULLIF(p.total_value, 0)
    INTO v_percentage
    FROM "HOLDING" h
    JOIN "STOCK" s ON s.stock_id = h.stock_id
    JOIN "PORTFOLIO" p ON p.portfolio_id = h.portfolio_id
    WHERE h.portfolio_id = v_portfolio_id
      AND h.stock_id = NEW.stock_id;

    IF v_percentage IS NOT NULL
       AND v_percentage > r.threshold_value THEN

        INSERT INTO "BEHAVIORAL_ALERT"
            (
                alert_id, trade_id, rule_id, pattern_type,
                severity, message, detected_at, acknowledged
            )
        VALUES
            (
                'ALT-' || gen_random_uuid()::TEXT,
                NEW.trade_id,
                r.rule_id,
                r.pattern_type,
                'MEDIUM',
                format(
                    'Stock concentration is %.2f%%; limit is %s%%.',
                    v_percentage,
                    r.threshold_value
                ),
                CURRENT_TIMESTAMP,
                FALSE
            );

    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_50_concentration ON "TRADE";

CREATE TRIGGER trg_50_concentration
AFTER INSERT ON "TRADE"
FOR EACH ROW
EXECUTE FUNCTION fn_check_concentration();