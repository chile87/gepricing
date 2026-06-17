-- GePricing — PostgreSQL 16 initial schema
-- Runs automatically on first container start via docker-entrypoint-initdb.d
--
-- Design goals:
-- 1. Support the current website layout: dashboard, inbox, strategy studio, alerts.
-- 2. Preserve the core table names already present in the repository where practical.
-- 3. Store time-series market changes so the UI can refresh in near real time.
-- 4. Keep enough audit history for recommendation approvals and applied price changes.

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Utility Functions ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION publish_ui_change()
RETURNS TRIGGER AS $$
DECLARE
    next_entity_id UUID;
BEGIN
    next_entity_id = COALESCE(NEW.id, OLD.id);

    INSERT INTO ui_change_feed (entity_type, entity_id, event_type, payload)
    VALUES (
        TG_TABLE_NAME,
        next_entity_id,
        TG_OP,
        CASE
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)
            ELSE to_jsonb(NEW)
        END
    );

    PERFORM pg_notify(
        'ui_change_feed',
        json_build_object(
            'entity_type', TG_TABLE_NAME,
            'entity_id', next_entity_id,
            'event_type', TG_OP
        )::text
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── Reference Data ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code        VARCHAR(64) NOT NULL UNIQUE,
    name        VARCHAR(128) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS competitor_sources (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code        VARCHAR(64) NOT NULL UNIQUE,
    name        VARCHAR(128) NOT NULL,
    base_url    TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_by      VARCHAR(128),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_strategies_status CHECK (status IN ('draft', 'active', 'paused', 'archived'))
);

CREATE TABLE IF NOT EXISTS strategy_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id     UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    rule_type       VARCHAR(64) NOT NULL,
    rule_name       VARCHAR(128) NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 100,
    config          JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Product Master ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skus (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_code            VARCHAR(64) NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    category_id         UUID REFERENCES categories(id) ON DELETE SET NULL,
    category            VARCHAR(128) NOT NULL,
    brand               VARCHAR(128),
    cost_price          NUMERIC(14, 2) NOT NULL,
    current_price       NUMERIC(14, 2) NOT NULL,
    currency            VARCHAR(8) NOT NULL DEFAULT 'USD',
    inventory           INTEGER NOT NULL DEFAULT 0,
    reorder_point       INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_skus_cost_price CHECK (cost_price >= 0),
    CONSTRAINT chk_skus_current_price CHECK (current_price >= 0),
    CONSTRAINT chk_skus_inventory CHECK (inventory >= 0)
);

CREATE TABLE IF NOT EXISTS competitor_listings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id                  UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    competitor_source_id    UUID NOT NULL REFERENCES competitor_sources(id) ON DELETE CASCADE,
    competitor_sku          VARCHAR(128),
    competitor_product_name TEXT,
    product_url             TEXT NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (sku_id, competitor_source_id, product_url)
);

-- ── Operational / Time-Series Data ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crawler_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       UUID REFERENCES competitor_sources(id) ON DELETE SET NULL,
    status          VARCHAR(32) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    pages_crawled   INTEGER NOT NULL DEFAULT 0,
    items_found     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_crawler_runs_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'partial'))
);

CREATE TABLE IF NOT EXISTS competitor_prices (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id                  UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    competitor_source_id    UUID REFERENCES competitor_sources(id) ON DELETE SET NULL,
    competitor_listing_id   UUID REFERENCES competitor_listings(id) ON DELETE SET NULL,
    crawler_run_id          UUID REFERENCES crawler_runs(id) ON DELETE SET NULL,
    source                  VARCHAR(64) NOT NULL,
    price                   NUMERIC(14, 2) NOT NULL,
    original_price          NUMERIC(14, 2),
    promo_price             NUMERIC(14, 2),
    currency                VARCHAR(8) NOT NULL DEFAULT 'USD',
    availability            VARCHAR(32),
    stock_status            VARCHAR(32),
    url                     TEXT,
    crawled_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_competitor_prices_price CHECK (price >= 0)
);

CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id          UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    on_hand_qty     INTEGER NOT NULL,
    reserved_qty    INTEGER NOT NULL DEFAULT 0,
    inbound_qty     INTEGER NOT NULL DEFAULT 0,
    snapshot_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_inventory_snapshots_on_hand CHECK (on_hand_qty >= 0),
    CONSTRAINT chk_inventory_snapshots_reserved CHECK (reserved_qty >= 0),
    CONSTRAINT chk_inventory_snapshots_inbound CHECK (inbound_qty >= 0),
    UNIQUE (sku_id, snapshot_at)
);

CREATE TABLE IF NOT EXISTS sales_metrics_hourly (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id              UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    period_start        TIMESTAMPTZ NOT NULL,
    units_sold          INTEGER NOT NULL DEFAULT 0,
    revenue             NUMERIC(14, 2) NOT NULL DEFAULT 0,
    margin_value        NUMERIC(14, 2) NOT NULL DEFAULT 0,
    promo_spend         NUMERIC(14, 2) NOT NULL DEFAULT 0,
    conversion_rate     NUMERIC(8, 4),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_sales_metrics_units_sold CHECK (units_sold >= 0),
    UNIQUE (sku_id, period_start)
);

-- ── Decisioning / Engine Output ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategy_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id         UUID REFERENCES strategies(id) ON DELETE SET NULL,
    triggered_by        VARCHAR(64) NOT NULL,
    status              VARCHAR(32) NOT NULL,
    run_started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_finished_at     TIMESTAMPTZ,
    input_snapshot      JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_summary      JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_strategy_runs_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS price_recommendations (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_run_id         UUID REFERENCES strategy_runs(id) ON DELETE SET NULL,
    strategy_id             UUID REFERENCES strategies(id) ON DELETE SET NULL,
    sku_id                  UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    recommendation_type     VARCHAR(32) NOT NULL,
    current_price           NUMERIC(14, 2) NOT NULL,
    recommended_price       NUMERIC(14, 2) NOT NULL,
    margin_pct              NUMERIC(6, 2),
    expected_revenue_impact NUMERIC(14, 2),
    expected_margin_impact  NUMERIC(14, 2),
    expected_inventory_impact NUMERIC(14, 2),
    confidence_score        NUMERIC(5, 2),
    confidence_label        VARCHAR(16),
    rule_details            JSONB NOT NULL DEFAULT '{}'::jsonb,
    rationale               JSONB NOT NULL DEFAULT '{}'::jsonb,
    status                  VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_price_recommendations_type CHECK (recommendation_type IN ('raise', 'lower', 'promo', 'stop', 'hold')),
    CONSTRAINT chk_price_recommendations_status CHECK (status IN ('pending', 'approved', 'rejected', 'applied', 'expired')),
    CONSTRAINT chk_price_recommendations_confidence_label CHECK (confidence_label IS NULL OR confidence_label IN ('Low', 'Medium', 'High'))
);

CREATE TABLE IF NOT EXISTS price_comparisons (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id                  UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE UNIQUE,
    competitor_count        INTEGER NOT NULL DEFAULT 0,
    lowest_competitor_price NUMERIC(14, 2),
    average_competitor_price NUMERIC(14, 2),
    highest_competitor_price NUMERIC(14, 2),
    price_gap_value         NUMERIC(14, 2),
    price_gap_pct           NUMERIC(8, 2),
    lowest_competitor_source VARCHAR(64),
    snapshot_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_price_comparisons_competitor_count CHECK (competitor_count >= 0)
);

CREATE TABLE IF NOT EXISTS approval_log (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id   UUID NOT NULL REFERENCES price_recommendations(id) ON DELETE CASCADE,
    action              VARCHAR(32) NOT NULL,
    actor               VARCHAR(128),
    notes               TEXT,
    acted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_approval_log_action CHECK (action IN ('approved', 'rejected', 'reopened'))
);

CREATE TABLE IF NOT EXISTS recommendation_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id   UUID NOT NULL REFERENCES price_recommendations(id) ON DELETE CASCADE,
    event_type          VARCHAR(32) NOT NULL,
    actor               VARCHAR(128),
    notes               TEXT,
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS applied_price_changes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id   UUID REFERENCES price_recommendations(id) ON DELETE SET NULL,
    sku_id              UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    old_price           NUMERIC(14, 2) NOT NULL,
    new_price           NUMERIC(14, 2) NOT NULL,
    applied_by          VARCHAR(128),
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    change_reason       TEXT
);

-- ── Alerting / Realtime Feed ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_alerts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id              UUID REFERENCES skus(id) ON DELETE CASCADE,
    competitor_price_id UUID REFERENCES competitor_prices(id) ON DELETE SET NULL,
    alert_type          VARCHAR(32) NOT NULL,
    severity            VARCHAR(16) NOT NULL,
    title               VARCHAR(255) NOT NULL,
    message             TEXT,
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_market_alerts_type CHECK (alert_type IN ('competitor_drop', 'competitor_rise', 'inventory_risk', 'margin_risk', 'new_recommendation')),
    CONSTRAINT chk_market_alerts_severity CHECK (severity IN ('info', 'warning', 'critical'))
);

CREATE TABLE IF NOT EXISTS ui_change_feed (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(64) NOT NULL,
    entity_id       UUID,
    event_type      VARCHAR(32) NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Helpful Views ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW latest_competitor_prices AS
SELECT DISTINCT ON (cp.sku_id, cp.source)
    cp.id,
    cp.sku_id,
    cp.source,
    cp.price,
    cp.original_price,
    cp.promo_price,
    cp.currency,
    cp.availability,
    cp.stock_status,
    cp.url,
    cp.crawled_at
FROM competitor_prices cp
ORDER BY cp.sku_id, cp.source, cp.crawled_at DESC;

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_categories_code
    ON categories(code);

CREATE INDEX IF NOT EXISTS idx_competitor_sources_code
    ON competitor_sources(code);

CREATE INDEX IF NOT EXISTS idx_skus_category_id
    ON skus(category_id);

CREATE INDEX IF NOT EXISTS idx_skus_is_active
    ON skus(is_active);

CREATE INDEX IF NOT EXISTS idx_competitor_listings_sku_id
    ON competitor_listings(sku_id);

CREATE INDEX IF NOT EXISTS idx_competitor_listings_source_id
    ON competitor_listings(competitor_source_id);

CREATE INDEX IF NOT EXISTS idx_crawler_runs_status_started_at
    ON crawler_runs(status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_competitor_prices_sku_id
    ON competitor_prices(sku_id);

CREATE INDEX IF NOT EXISTS idx_competitor_prices_source
    ON competitor_prices(source);

CREATE INDEX IF NOT EXISTS idx_competitor_prices_source_id_crawled_at
    ON competitor_prices(competitor_source_id, crawled_at DESC);

CREATE INDEX IF NOT EXISTS idx_competitor_prices_sku_id_crawled_at
    ON competitor_prices(sku_id, crawled_at DESC);

CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_sku_id_snapshot_at
    ON inventory_snapshots(sku_id, snapshot_at DESC);

CREATE INDEX IF NOT EXISTS idx_sales_metrics_hourly_sku_id_period_start
    ON sales_metrics_hourly(sku_id, period_start DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_rules_strategy_id_priority
    ON strategy_rules(strategy_id, priority);

CREATE INDEX IF NOT EXISTS idx_strategy_runs_strategy_id_status
    ON strategy_runs(strategy_id, status);

CREATE INDEX IF NOT EXISTS idx_price_recs_sku_id
    ON price_recommendations(sku_id);

CREATE INDEX IF NOT EXISTS idx_price_recs_status
    ON price_recommendations(status);

CREATE INDEX IF NOT EXISTS idx_price_recs_type_created_at
    ON price_recommendations(recommendation_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_price_recs_strategy_run_id
    ON price_recommendations(strategy_run_id);

CREATE INDEX IF NOT EXISTS idx_price_comparisons_sku_id
    ON price_comparisons(sku_id);

CREATE INDEX IF NOT EXISTS idx_price_comparisons_snapshot_at
    ON price_comparisons(snapshot_at DESC);

CREATE INDEX IF NOT EXISTS idx_approval_log_rec_id
    ON approval_log(recommendation_id);

CREATE INDEX IF NOT EXISTS idx_recommendation_events_rec_id_created_at
    ON recommendation_events(recommendation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_applied_price_changes_sku_id_applied_at
    ON applied_price_changes(sku_id, applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_alerts_is_read_created_at
    ON market_alerts(is_read, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ui_change_feed_created_at
    ON ui_change_feed(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ui_change_feed_entity_type_entity_id
    ON ui_change_feed(entity_type, entity_id, created_at DESC);

-- ── Triggers ──────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_competitor_sources_set_updated_at ON competitor_sources;
CREATE TRIGGER trg_competitor_sources_set_updated_at
BEFORE UPDATE ON competitor_sources
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_strategies_set_updated_at ON strategies;
CREATE TRIGGER trg_strategies_set_updated_at
BEFORE UPDATE ON strategies
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_strategy_rules_set_updated_at ON strategy_rules;
CREATE TRIGGER trg_strategy_rules_set_updated_at
BEFORE UPDATE ON strategy_rules
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_skus_set_updated_at ON skus;
CREATE TRIGGER trg_skus_set_updated_at
BEFORE UPDATE ON skus
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_competitor_listings_set_updated_at ON competitor_listings;
CREATE TRIGGER trg_competitor_listings_set_updated_at
BEFORE UPDATE ON competitor_listings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_price_recommendations_set_updated_at ON price_recommendations;
CREATE TRIGGER trg_price_recommendations_set_updated_at
BEFORE UPDATE ON price_recommendations
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_competitor_prices_publish_ui_change ON competitor_prices;
CREATE TRIGGER trg_competitor_prices_publish_ui_change
AFTER INSERT OR UPDATE OR DELETE ON competitor_prices
FOR EACH ROW
EXECUTE FUNCTION publish_ui_change();

DROP TRIGGER IF EXISTS trg_price_recommendations_publish_ui_change ON price_recommendations;
CREATE TRIGGER trg_price_recommendations_publish_ui_change
AFTER INSERT OR UPDATE OR DELETE ON price_recommendations
FOR EACH ROW
EXECUTE FUNCTION publish_ui_change();

DROP TRIGGER IF EXISTS trg_market_alerts_publish_ui_change ON market_alerts;
CREATE TRIGGER trg_market_alerts_publish_ui_change
AFTER INSERT OR UPDATE OR DELETE ON market_alerts
FOR EACH ROW
EXECUTE FUNCTION publish_ui_change();

DROP TRIGGER IF EXISTS trg_applied_price_changes_publish_ui_change ON applied_price_changes;
CREATE TRIGGER trg_applied_price_changes_publish_ui_change
AFTER INSERT OR UPDATE OR DELETE ON applied_price_changes
FOR EACH ROW
EXECUTE FUNCTION publish_ui_change();

-- ── Seed Reference Rows ───────────────────────────────────────────────────────
INSERT INTO categories (code, name)
VALUES
    ('electronics', 'Electronics'),
    ('audio', 'Audio'),
    ('appliances', 'Appliances'),
    ('wearables', 'Wearables'),
    ('accessories', 'Accessories')
ON CONFLICT (code) DO NOTHING;

INSERT INTO competitor_sources (code, name, base_url)
VALUES
    ('tgdd', 'The Gioi Di Dong', 'https://www.thegioididong.com'),
    ('cellphones', 'CellphoneS', 'https://cellphones.com.vn'),
    ('hoangha', 'Hoang Ha Mobile', 'https://hoanghamobile.com')
ON CONFLICT (code) DO NOTHING;
