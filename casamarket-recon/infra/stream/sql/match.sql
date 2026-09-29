-- Streaming twin of dbt `fct_transaction_discrepancy` (category part), run by the Flink SQL client.
-- auths ⋈ settlements (interval join, 15 days = max settle lag) -> FX-adjusted residual -> category.
-- Same formulas as dbt: expected_settled_sql() and category_case() (tests/infra/test_stream.py checks
-- the CASE text against the dbt macro rendered with config/thresholds.yaml).
SET 'pipeline.name' = 'recon-stream-match';
SET 'parallelism.default' = '1';
-- The filesystem sink commits files on checkpoints. (SQL client: a statement ends with ';' at line end.)
SET 'execution.checkpointing.interval' = '10s';

-- ---------- sources ----------
CREATE TABLE auths (
    transaction_id STRING, merchant_id STRING, psp STRING, country STRING, currency STRING,
    payer_currency STRING, is_cross_border BOOLEAN, authorized_amount BIGINT,
    auth_ts TIMESTAMP(3), status STRING,
    WATERMARK FOR auth_ts AS auth_ts - INTERVAL '1' MINUTE
) WITH ('connector' = 'kafka', 'topic' = 'auths', 'properties.bootstrap.servers' = 'redpanda:9092',
        'properties.group.id' = 'recon-stream', 'scan.startup.mode' = 'earliest-offset',
        'format' = 'json', 'json.timestamp-format.standard' = 'SQL');

CREATE TABLE settlements (
    transaction_id STRING, psp STRING, currency STRING, settled_amount BIGINT, settle_ts TIMESTAMP(3),
    WATERMARK FOR settle_ts AS settle_ts - INTERVAL '1' MINUTE
) WITH ('connector' = 'kafka', 'topic' = 'settlements', 'properties.bootstrap.servers' = 'redpanda:9092',
        'properties.group.id' = 'recon-stream', 'scan.startup.mode' = 'earliest-offset',
        'format' = 'json', 'json.timestamp-format.standard' = 'SQL');

-- Small bounded reference tables (the CSV header row fails to parse -> nulls -> filtered out).
CREATE TABLE fx_rates (rate_date DATE, currency STRING, local_per_usd DOUBLE)
WITH ('connector' = 'filesystem', 'path' = 'file:///data/raw/fx_rates_daily.csv',
      'format' = 'csv', 'csv.ignore-parse-errors' = 'true');

CREATE TABLE currency_exponents (currency STRING, exponent INT)
WITH ('connector' = 'filesystem', 'path' = 'file:///data/seeds/currency_exponents.csv',
      'format' = 'csv', 'csv.ignore-parse-errors' = 'true');

-- ---------- sinks ----------
-- Column order = casarecon.stream.compare.SINK_COLUMNS (CSV has no header).
CREATE TABLE matched_sink (
    transaction_id STRING, psp STRING, country STRING, currency STRING, is_cross_border BOOLEAN,
    auth_ts TIMESTAMP(3), settle_ts TIMESTAMP(3), authorized_amount BIGINT, settled_amount BIGINT,
    fx_auth DOUBLE, fx_settle DOUBLE, expected_settled BIGINT, residual BIGINT,
    residual_pct DOUBLE, residual_usd DOUBLE, category STRING
) WITH ('connector' = 'filesystem', 'path' = 'file:///data/lake/stream/matched', 'format' = 'csv',
        'sink.rolling-policy.rollover-interval' = '30s', 'sink.rolling-policy.check-interval' = '10s');

CREATE TABLE large_sink (
    transaction_id STRING, psp STRING, country STRING, currency STRING, settle_ts TIMESTAMP(3),
    residual_usd DOUBLE, residual_pct DOUBLE, category STRING
) WITH ('connector' = 'kafka', 'topic' = 'large_discrepancies',
        'properties.bootstrap.servers' = 'redpanda:9092',
        'key.format' = 'raw', 'key.fields' = 'transaction_id',
        'value.format' = 'json', 'value.json.timestamp-format.standard' = 'SQL');

-- ---------- logic ----------
CREATE TEMPORARY VIEW matched AS
SELECT a.transaction_id, a.psp, a.country, a.currency, a.is_cross_border,
       CAST(a.auth_ts AS TIMESTAMP(3)) AS auth_ts, CAST(s.settle_ts AS TIMESTAMP(3)) AS settle_ts,
       a.authorized_amount, s.settled_amount
FROM auths a
JOIN settlements s
  ON s.transaction_id = a.transaction_id
 AND s.settle_ts BETWEEN a.auth_ts AND a.auth_ts + INTERVAL '15' DAY
WHERE a.status <> 'failed';

-- fx_auth / fx_settle: rate on the auth day / settle day (int_transactions_usd).
CREATE TEMPORARY VIEW priced AS
SELECT m.*, fa.local_per_usd AS fx_auth, fs.local_per_usd AS fx_settle, e.exponent
FROM matched m
JOIN fx_rates fa ON fa.currency = m.currency AND fa.rate_date = CAST(m.auth_ts AS DATE)
JOIN fx_rates fs ON fs.currency = m.currency AND fs.rate_date = CAST(m.settle_ts AS DATE)
JOIN currency_exponents e ON e.currency = m.currency;

-- expected = auth x fx_settle / fx_auth (cross-border) or auth; residual = settled - expected.
CREATE TEMPORARY VIEW expected AS
SELECT *,
    'settled' AS status,                            -- a settlement event means status = settled
    settled_amount - authorized_amount AS diff_local,
    CASE WHEN is_cross_border
         THEN CAST(ROUND(authorized_amount * fx_settle / fx_auth, 0) AS BIGINT)
         ELSE authorized_amount END AS expected_settled
FROM priced;

CREATE TEMPORARY VIEW money AS
SELECT *,
    settled_amount - expected_settled AS residual,
    ROUND(100.0 * CAST(settled_amount - expected_settled AS DOUBLE) / expected_settled, 4) AS residual_pct,
    ROUND(CAST(settled_amount - expected_settled AS DOUBLE) / POWER(10, exponent) / fx_auth, 2) AS residual_usd,
    ABS(ROUND(CAST(settled_amount - expected_settled AS DOUBLE) / POWER(10, exponent) / fx_auth, 2))
        AS abs_residual_usd
FROM expected;

-- Category: first match wins. Keep this CASE identical to dbt category_case(t, 'abs_residual_usd').
CREATE TEMPORARY VIEW categorized AS
SELECT *,
    case
        when status <> 'settled' then null
        when diff_local = 0 then 'exact'
        when abs(diff_local) <= 1 then 'rounding'
        when abs(residual_pct) <= 2 and abs_residual_usd < 20 then 'fx_tolerance'
        when abs(residual_pct) <= 5 and abs_residual_usd < 20 then 'meaningful'
        else 'large'
    end AS category
FROM money;

EXECUTE STATEMENT SET
BEGIN
INSERT INTO matched_sink
SELECT transaction_id, psp, country, currency, is_cross_border, auth_ts, settle_ts, authorized_amount,
       settled_amount, fx_auth, fx_settle, expected_settled, residual, residual_pct, residual_usd, category
FROM categorized;
INSERT INTO large_sink
SELECT transaction_id, psp, country, currency, settle_ts, residual_usd, residual_pct, category
FROM categorized WHERE category = 'large';
END;
