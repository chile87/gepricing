-- GePricing — PostgreSQL 16 initial schema
-- Runs automatically on first container start via docker-entrypoint-initdb.d

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── skus ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skus (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_code    VARCHAR(64)  NOT NULL UNIQUE,
    name        TEXT         NOT NULL,
    category    VARCHAR(128) NOT NULL,
    cost_price  NUMERIC(14, 2) NOT NULL,
    current_price NUMERIC(14, 2) NOT NULL,
    inventory   INTEGER      NOT NULL DEFAULT 0,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── competitor_prices ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS competitor_prices (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id      UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    source      VARCHAR(64)    NOT NULL,   -- e.g. 'tgdd', 'cellphones', 'hoangha'
    price       NUMERIC(14, 2) NOT NULL,
    url         TEXT,
    crawled_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- ── price_recommendations ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_recommendations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id              UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    recommended_price   NUMERIC(14, 2) NOT NULL,
    margin_pct          NUMERIC(6, 2),
    rule_details        JSONB,            -- snapshot of rule outputs
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── approval_log ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS approval_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id UUID NOT NULL REFERENCES price_recommendations(id) ON DELETE CASCADE,
    action          VARCHAR(32) NOT NULL,  -- 'approved' | 'rejected'
    actor           VARCHAR(128),
    notes           TEXT,
    acted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_competitor_prices_sku_id   ON competitor_prices(sku_id);
CREATE INDEX IF NOT EXISTS idx_competitor_prices_source   ON competitor_prices(source);
CREATE INDEX IF NOT EXISTS idx_price_recs_sku_id          ON price_recommendations(sku_id);
CREATE INDEX IF NOT EXISTS idx_price_recs_status          ON price_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_approval_log_rec_id        ON approval_log(recommendation_id);
