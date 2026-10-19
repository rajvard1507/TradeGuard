CREATE TABLE IF NOT EXISTS "USER" (
    user_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "TRADER" (
    trader_id VARCHAR(10) PRIMARY KEY,
    user_id VARCHAR(10) NOT NULL UNIQUE,
    account_balance NUMERIC(15, 2) NOT NULL DEFAULT 0,
    margin_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    kyc_verified BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT trader_user_fk
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
);

CREATE TABLE IF NOT EXISTS "ADMIN" (
    admin_id VARCHAR(10) PRIMARY KEY,
    user_id VARCHAR(10) NOT NULL UNIQUE,
    department VARCHAR(100),
    access_level VARCHAR(50),
    CONSTRAINT admin_user_fk
        FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id)
);

CREATE TABLE IF NOT EXISTS "STOCK" (
    stock_id VARCHAR(10) PRIMARY KEY,
    ticker_symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(100) NOT NULL,
    sector VARCHAR(100),
    current_price NUMERIC(15, 2) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "PORTFOLIO" (
    portfolio_id VARCHAR(10) PRIMARY KEY,
    trader_id VARCHAR(10) NOT NULL UNIQUE,
    cash_balance NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_value NUMERIC(15, 2) NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT portfolio_trader_fk
        FOREIGN KEY (trader_id)
        REFERENCES "TRADER"(trader_id)
);

CREATE TABLE IF NOT EXISTS "HOLDING" (
    portfolio_id VARCHAR(10) NOT NULL,
    stock_id VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    avg_buy_price NUMERIC(15, 2) NOT NULL,
    PRIMARY KEY (portfolio_id, stock_id),
    CONSTRAINT holding_portfolio_fk
        FOREIGN KEY (portfolio_id)
        REFERENCES "PORTFOLIO"(portfolio_id),
    CONSTRAINT holding_stock_fk
        FOREIGN KEY (stock_id)
        REFERENCES "STOCK"(stock_id)
);

CREATE TABLE IF NOT EXISTS "TRADE" (
    trade_id VARCHAR(10) PRIMARY KEY,
    trader_id VARCHAR(10) NOT NULL,
    stock_id VARCHAR(10) NOT NULL,
    trade_type VARCHAR(10) NOT NULL
        CHECK (trade_type IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_per_share NUMERIC(15, 2) NOT NULL,
    leverage_ratio NUMERIC(10, 2) NOT NULL DEFAULT 1,
    trade_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL DEFAULT 'EXECUTED',
    realized_pnl NUMERIC(15, 2),
    CONSTRAINT trade_trader_fk
        FOREIGN KEY (trader_id)
        REFERENCES "TRADER"(trader_id),
    CONSTRAINT trade_stock_fk
        FOREIGN KEY (stock_id)
        REFERENCES "STOCK"(stock_id)
);

CREATE TABLE IF NOT EXISTS "RISK_RULE" (
    rule_id VARCHAR(10) PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    parameter_name VARCHAR(100) NOT NULL,
    threshold_value NUMERIC(15, 4) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS "BEHAVIORAL_ALERT" (
    alert_id VARCHAR(10) PRIMARY KEY,
    trade_id VARCHAR(10) NOT NULL,
    rule_id VARCHAR(10) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    severity VARCHAR(30) NOT NULL,
    message TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT behavioral_alert_trade_fk
        FOREIGN KEY (trade_id)
        REFERENCES "TRADE"(trade_id),
    CONSTRAINT behavioral_alert_rule_fk
        FOREIGN KEY (rule_id)
        REFERENCES "RISK_RULE"(rule_id)
);

CREATE TABLE IF NOT EXISTS "ADMIN_REVIEW" (
    review_id VARCHAR(10) PRIMARY KEY,
    admin_id VARCHAR(10) NOT NULL,
    alert_id VARCHAR(10) NOT NULL UNIQUE,
    notes TEXT,
    action_taken VARCHAR(100),
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT admin_review_admin_fk
        FOREIGN KEY (admin_id)
        REFERENCES "ADMIN"(admin_id),
    CONSTRAINT admin_review_alert_fk
        FOREIGN KEY (alert_id)
        REFERENCES "BEHAVIORAL_ALERT"(alert_id)
);