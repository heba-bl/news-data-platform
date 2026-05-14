-- ============================================================
-- NEWS DATA WAREHOUSE SCHEMA
-- ============================================================

-- ─── DIMENSIONS ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_source (
    source_id   SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(50),
    language    VARCHAR(10),
    base_url    TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_category (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     SERIAL PRIMARY KEY,
    full_date   DATE NOT NULL UNIQUE,
    day         INT,
    month       INT,
    year        INT,
    quarter     INT,
    day_of_week INT,
    week_of_year INT
);

-- ─── FACT TABLE ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fact_articles (
    article_id   SERIAL PRIMARY KEY,
    title        TEXT NOT NULL,
    author       VARCHAR(200),
    published_at TIMESTAMP,
    date_id      INT REFERENCES dim_date(date_id),
    source_id    INT REFERENCES dim_source(source_id),
    category_id  INT REFERENCES dim_category(category_id),
    content      TEXT,
    url          TEXT UNIQUE NOT NULL,
    language     VARCHAR(10),
    word_count   INT DEFAULT 0,
    scraped_at   TIMESTAMP,
    processed_at TIMESTAMP,
    inserted_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_date ON fact_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_source ON fact_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_category ON fact_articles(category_id);
CREATE INDEX IF NOT EXISTS idx_articles_language ON fact_articles(language);

-- ─── ANALYTICS TABLES (GOLD LAYER MATERIALIZED) ─────────────

CREATE TABLE IF NOT EXISTS agg_articles_by_day (
    id           SERIAL PRIMARY KEY,
    date         DATE NOT NULL,
    article_count INT NOT NULL,
    computed_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(date)
);

CREATE TABLE IF NOT EXISTS agg_articles_by_source (
    id             SERIAL PRIMARY KEY,
    source_name    VARCHAR(100) NOT NULL,
    article_count  INT NOT NULL,
    avg_word_count INT,
    computed_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_name)
);

CREATE TABLE IF NOT EXISTS agg_articles_by_category (
    id             SERIAL PRIMARY KEY,
    category_name  VARCHAR(100),
    source_name    VARCHAR(100),
    article_count  INT NOT NULL,
    computed_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(category_name, source_name)
);

CREATE TABLE IF NOT EXISTS agg_top_keywords (
    id          SERIAL PRIMARY KEY,
    keyword     VARCHAR(200) NOT NULL UNIQUE,
    frequency   INT NOT NULL,
    computed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agg_language_distribution (
    id            SERIAL PRIMARY KEY,
    language      VARCHAR(10) NOT NULL UNIQUE,
    article_count INT NOT NULL,
    computed_at   TIMESTAMP DEFAULT NOW()
);

-- ─── GOVERNANCE TABLES ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id       SERIAL PRIMARY KEY,
    pipeline     VARCHAR(100) NOT NULL,
    started_at   TIMESTAMP NOT NULL,
    finished_at  TIMESTAMP,
    status       VARCHAR(20) DEFAULT 'running',
    records_in   INT DEFAULT 0,
    records_out  INT DEFAULT 0,
    error_msg    TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_log (
    log_id      SERIAL PRIMARY KEY,
    pipeline    VARCHAR(100),
    run_date    TIMESTAMP DEFAULT NOW(),
    total       INT,
    passed      INT,
    failed      INT,
    pass_rate   NUMERIC(5,2),
    issues      JSONB
);

-- ─── SEED SOURCES ───────────────────────────────────────────

INSERT INTO dim_source (source_name, country, language, base_url) VALUES
    ('Hespress',   'Morocco',        'ar', 'https://hespress.com'),
    ('Akhbarona',  'Morocco',        'ar', 'https://www.akhbarona.com'),
    ('BBC',        'United Kingdom', 'en', 'https://www.bbc.com'),
    ('CNN',        'United States',  'en', 'https://edition.cnn.com'),
    ('Reuters',    'United Kingdom', 'en', 'https://www.reuters.com')
ON CONFLICT (source_name) DO NOTHING;
