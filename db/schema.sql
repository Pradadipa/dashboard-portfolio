-- ============================================================================
-- Shopify orders schema (PostgreSQL)
--
-- Target of the order sync in notebooks/shopify.ipynb:
--   * QUERY_ORDER (GraphQL)  -> customers, orders, order_discounts,
--                               order_line_items, line_item_discount_allocations
--   * customerJourneySummary + REST client_details -> order_attribution
--
-- Conventions:
--   * Primary keys are Shopify's numeric ids (the tail of the gid,
--     e.g. gid://shopify/Order/7090088542256 -> 7090088542256).
--   * Money is NUMERIC(12,2) + a currency column (Shopify sends strings).
--   * Re-sync pattern: upsert parents (ON CONFLICT DO UPDATE); for children
--     delete-and-reinsert per order_id, mirroring merge_orders() in Sheets.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS shopify;

-- ----------------------------------------------------------------------------
-- customers — one row per Shopify customer, enriched by QUERY_CUSTOMER
-- (first purchase + default-address location + lifetime stats).
-- Lifetime fields (number_of_orders, amount_spent) are Shopify-computed
-- snapshots — overwrite them on every sync, don't increment locally.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.customers (
    customer_id       BIGINT PRIMARY KEY,        -- from customer.id gid
    email             TEXT,                      -- defaultEmailAddress.emailAddress
    display_name      TEXT,
    customer_since    TIMESTAMPTZ,               -- Shopify customer.createdAt
    first_purchase_at TIMESTAMPTZ,               -- createdAt of oldest order
    first_order_id    BIGINT,                    -- no FK: order may predate synced range
    last_order_at     TIMESTAMPTZ,               -- customer.lastOrder.createdAt
    last_order_id     BIGINT,                    -- no FK, same reason as first_order_id
    last_visit_at     TIMESTAMPTZ,               -- visit that led to the last order
    last_visit_source TEXT,                      --   (Shopify has no standalone visit log)
    number_of_orders  INTEGER NOT NULL DEFAULT 0,
    amount_spent      NUMERIC(12,2),             -- lifetime total
    currency          CHAR(3),
    city              TEXT,                      -- defaultAddress (current, not
    province          TEXT,                      --   address-at-first-purchase)
    province_code     TEXT,                      -- "FL", "WA", ...
    country           TEXT,
    country_code      CHAR(2),                   -- ISO 3166-1, "US", ...
    zip               TEXT,
    tags              TEXT,                      -- comma-separated Shopify tags
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customers_email          ON shopify.customers (email);
CREATE INDEX IF NOT EXISTS idx_customers_location       ON shopify.customers (country_code, province_code);
CREATE INDEX IF NOT EXISTS idx_customers_first_purchase ON shopify.customers (first_purchase_at);

-- ----------------------------------------------------------------------------
-- orders — one row per order
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.orders (
    order_id            BIGINT PRIMARY KEY,      -- from order.id gid
    order_name          TEXT NOT NULL,           -- "#285121"
    created_at          TIMESTAMPTZ NOT NULL,    -- Shopify createdAt
    financial_status    TEXT,                    -- PAID, REFUNDED, ...
    fulfillment_status  TEXT,                    -- FULFILLED, UNFULFILLED, ...
    cancelled_at        TIMESTAMPTZ,             -- NULL unless order cancelled
    cancel_reason       TEXT,                    -- CUSTOMER / FRAUD / INVENTORY / ...
    total_amount        NUMERIC(12,2),           -- original total at checkout (totalPriceSet)
    current_total       NUMERIC(12,2),           -- after edits/refunds (currentTotalPriceSet)
    total_paid          NUMERIC(12,2),           -- gross payments received (totalReceivedSet)
    total_refunded      NUMERIC(12,2),           -- refunded to date (totalRefundedSet)
    net_payment         NUMERIC(12,2),           -- paid − refunded (netPaymentSet); use for net revenue
    currency            CHAR(3),
    discount_code       TEXT,                    -- order-level discountCode
    customer_id         BIGINT REFERENCES shopify.customers (customer_id),
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now()
    
);

CREATE INDEX IF NOT EXISTS idx_orders_created_at  ON shopify.orders (created_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON shopify.orders (customer_id);

-- ----------------------------------------------------------------------------
-- order_attribution — 1:1 with orders; kept separate because attribution
-- arrives late (journey_ready = false on fresh orders) and device_type comes
-- from a second (REST) fetch. Re-runnable without touching orders.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.order_attribution (
    order_id            BIGINT PRIMARY KEY
                        REFERENCES shopify.orders (order_id) ON DELETE CASCADE,
    traffic_source      TEXT,                    -- google, facebook, direct, ...
    traffic_channel     TEXT,                    -- derived: Paid Search, Email, ...
    source_type         TEXT,                    -- Shopify MarketingTactic enum
    device_type         TEXT,                    -- mobile / tablet / desktop / other / unknown
    device_model        TEXT,                    -- 'Pixel 9', 'SM-S928U', 'iPhone', 'Mac';
                                                 --   Apple/Chrome hide models (see notebook note)
    user_agent          TEXT,
    referrer_url        TEXT,
    landing_page        TEXT,
    utm_source          TEXT,
    utm_medium          TEXT,
    utm_campaign        TEXT,
    utm_content         TEXT,
    utm_term            TEXT,
    days_to_conversion  INTEGER,
    journey_ready       BOOLEAN NOT NULL DEFAULT FALSE,  -- false -> re-fetch later
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attribution_channel ON shopify.order_attribution (traffic_channel);
CREATE INDEX IF NOT EXISTS idx_attribution_source  ON shopify.order_attribution (traffic_source);
CREATE INDEX IF NOT EXISTS idx_attribution_device  ON shopify.order_attribution (device_type);
CREATE INDEX IF NOT EXISTS idx_attribution_pending ON shopify.order_attribution (order_id)
    WHERE NOT journey_ready;                     -- fast "what needs a re-fetch" scan

-- ----------------------------------------------------------------------------
-- order_discounts — one row per discountApplications edge (N per order).
-- position = index in the discountApplications list; Shopify has no id here,
-- so (order_id, position) is the natural key.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.order_discounts (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id          BIGINT NOT NULL
                      REFERENCES shopify.orders (order_id) ON DELETE CASCADE,
    position          SMALLINT NOT NULL,         -- 0-based index in the list
    kind              TEXT NOT NULL CHECK (kind IN ('CODE', 'AUTOMATIC', 'MANUAL')),
    code_or_title     TEXT,                      -- code (CODE) or title (AUTOMATIC/MANUAL)
    description       TEXT,                      -- ManualDiscountApplication only
    value_amount      NUMERIC(12,2),             -- exactly one of amount / percentage
    value_percentage  NUMERIC(6,2),              --   is set (MoneyV2 vs PricingPercentageValue)
    currency          CHAR(3),
    allocation_method TEXT,                      -- EACH / ACROSS / ONE
    target_selection  TEXT,                      -- ALL / ENTITLED / EXPLICIT
    target_type       TEXT,                      -- LINE_ITEM / SHIPPING_LINE
    UNIQUE (order_id, position),
    CHECK (value_amount IS NOT NULL OR value_percentage IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_order_discounts_code ON shopify.order_discounts (code_or_title);

-- ----------------------------------------------------------------------------
-- order_line_items — one row per line item (N per order)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.order_line_items (
    line_item_id           BIGINT PRIMARY KEY,   -- from lineItems node id gid
    order_id               BIGINT NOT NULL
                           REFERENCES shopify.orders (order_id) ON DELETE CASCADE,
    sku                    TEXT,
    title                  TEXT,
    quantity               INTEGER NOT NULL,     -- as ordered (never changes)
    current_quantity       INTEGER,              -- after removals/refunds; 0 = line cancelled
    unfulfilled_quantity   INTEGER,              -- still waiting to ship
    non_fulfillable_quantity INTEGER,
    line_status            TEXT,                 -- derived: REMOVED / FULFILLED /
                                                 --   PARTIALLY_FULFILLED / UNFULFILLED
    original_unit_price    NUMERIC(12,2),
    discounted_unit_price  NUMERIC(12,2),        -- after ALL discounts incl. order-level
                                                 --   codes (GraphQL ...AfterAllDiscountsSet)
    currency               CHAR(3),
    season_code            TEXT,                 -- derived from SKU prefix (transform layer)
    -- units the customer sent back, from the Returns API (Order.returns with
    -- status OPEN/CLOSED — see transform/shopify_ingest._returned_quantities).
    -- NOT derived from refund restockType: 'RETURN' has been extinct since
    -- early 2024 (Redo writes NO_RESTOCK and records the Return separately),
    -- so a restockType-based rule reads 0 for every recent period.
    -- Validated 2026-07-30 over 1,130 refund lines — see
    -- docs/net-sales-definition.md §4.2.
    returned_quantity      INTEGER NOT NULL DEFAULT 0,
    is_returned            BOOLEAN GENERATED ALWAYS AS (returned_quantity > 0) STORED,
    -- net sales per line, Shopify-style: price after all discounts × units not
    -- cancelled/returned (excludes tax & shipping; $-only partial refunds not reflected)
    net_sales              NUMERIC(12,2) GENERATED ALWAYS AS
                             (discounted_unit_price * current_quantity) STORED
);
-- idempotent upgrades for databases created before these columns existed
ALTER TABLE shopify.order_line_items ADD COLUMN IF NOT EXISTS
    net_sales NUMERIC(12,2) GENERATED ALWAYS AS
        (discounted_unit_price * current_quantity) STORED;
ALTER TABLE shopify.order_line_items ADD COLUMN IF NOT EXISTS
    returned_quantity INTEGER NOT NULL DEFAULT 0;
ALTER TABLE shopify.order_line_items ADD COLUMN IF NOT EXISTS
    is_returned BOOLEAN GENERATED ALWAYS AS (returned_quantity > 0) STORED;

CREATE INDEX IF NOT EXISTS idx_line_items_order_id ON shopify.order_line_items (order_id);
CREATE INDEX IF NOT EXISTS idx_line_items_sku      ON shopify.order_line_items (sku);

-- ----------------------------------------------------------------------------
-- refund_line_items — one row per refunded line per refund event.
-- The money side of returns: Shopify's Sales report books the negative
-- "Returns" value at processed_at (refund createdAt), NOT the order date.
-- Net Sales for a period = orders created in period − subtotals processed
-- in period. subtotal = product value only (no tax/shipping).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.refund_line_items (
    -- surrogate key: (refund_id, line_item_id) is NOT unique — one refund can
    -- legitimately hold several entries for the same line (e.g. a 2-unit line
    -- refunded as two 1-unit events; verified in production data 2026-07-11)
    id           BIGINT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    refund_id    BIGINT  NOT NULL,                -- from Refund gid
    order_id     BIGINT  NOT NULL
                 REFERENCES shopify.orders (order_id) ON DELETE CASCADE,
    line_item_id BIGINT  NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL,            -- refund createdAt
    quantity     INTEGER NOT NULL,
    subtotal     NUMERIC(12,2) NOT NULL,
    restock_type TEXT                             -- RETURN / CANCEL / NO_RESTOCK / ...
);

CREATE INDEX IF NOT EXISTS idx_refund_lines_processed ON shopify.refund_line_items (processed_at);
CREATE INDEX IF NOT EXISTS idx_refund_lines_order     ON shopify.refund_line_items (order_id);

-- ----------------------------------------------------------------------------
-- refunds — one row per refund EVENT (the header), with its all-in total.
--
-- Why this exists alongside refund_line_items: Shopify lets a refund carry
-- money WITHOUT allocating it to any line item — staff type an amount, a
-- returns app (Redo) issues it, or it is goodwill for a missed discount code.
-- Those refunds have an empty refundLineItems, so refund_line_items holds
-- nothing for them and the money is invisible at line grain. Measured
-- 2026-07-27: 578 orders / $39,953 of refunds with no line allocation at all.
--
-- total_refunded is the CASH returned (product + tax + shipping), which is
-- 0.00 when a return is settled as store credit / gift card / exchange.
-- refund_line_items.subtotal is instead the product value of the goods named.
-- The two are NOT comparable — use v_refund_reconciliation below rather than
-- subtracting one from the other.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.refunds (
    refund_id      BIGINT PRIMARY KEY,          -- from Refund gid
    order_id       BIGINT NOT NULL
                   REFERENCES shopify.orders (order_id) ON DELETE CASCADE,
    processed_at   TIMESTAMPTZ NOT NULL,        -- refund createdAt
    total_refunded NUMERIC(12,2) NOT NULL,      -- product + tax + shipping
    currency       CHAR(3),
    note           TEXT                         -- "Redo", "Damaged item received", ...
);

CREATE INDEX IF NOT EXISTS idx_refunds_processed ON shopify.refunds (processed_at);
CREATE INDEX IF NOT EXISTS idx_refunds_order     ON shopify.refunds (order_id);

-- Per-refund reconciliation: cash returned vs value booked against line items.
--
-- The two columns measure DIFFERENT things and must not be netted naively:
--   total_refunded     cash actually returned (Refund.totalRefundedSet). It is
--                      0.00 whenever a return is settled as store credit, a
--                      gift card or an exchange — 53 of 184 refunds in a June
--                      2026 sample had goods come back with zero cash out.
--   allocated_subtotal product value of the lines the refund names, excluding
--                      tax and shipping (SUM of refund_line_items.subtotal).
-- Subtracting one from the other yields negative noise for ~1/3 of refunds.
--
-- unallocated_refund isolates the case Net Sales genuinely misses: a refund
-- that moved money while naming NO line item, so nothing anywhere reduces
-- product revenue. It is 0 for every refund that did name lines, which keeps
-- SUM(unallocated_refund) safe to add to a returns figure.
-- DROP first: CREATE OR REPLACE cannot rename or reorder a view's columns, and
-- this view's shape changed after its first release. Plain DROP (not CASCADE)
-- so it fails loudly if anything ever comes to depend on it. apply_schema runs
-- the whole file in one transaction, so there is no window where it is missing.
DROP VIEW IF EXISTS shopify.v_refund_reconciliation;
CREATE VIEW shopify.v_refund_reconciliation AS
SELECT
    r.refund_id,
    r.order_id,
    (r.processed_at AT TIME ZONE 'America/New_York')::date AS processed_date,
    r.total_refunded,
    COALESCE(SUM(rli.subtotal), 0)                         AS allocated_subtotal,
    COUNT(rli.id)                                          AS refund_line_count,
    CASE WHEN COUNT(rli.id) = 0 THEN r.total_refunded ELSE 0 END
                                                           AS unallocated_refund,
    r.note
FROM shopify.refunds r
LEFT JOIN shopify.refund_line_items rli ON rli.refund_id = r.refund_id
GROUP BY r.refund_id, r.order_id, r.processed_at, r.total_refunded, r.note;

-- ----------------------------------------------------------------------------
-- line_item_discount_allocations — one row per discountAllocations entry
-- (N per line item): how much of which discount landed on which line.
-- The GraphQL payload references the application by code/title; resolve it
-- to order_discounts.id during load (match on order_id + code_or_title).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.line_item_discount_allocations (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    line_item_id       BIGINT NOT NULL
                       REFERENCES shopify.order_line_items (line_item_id) ON DELETE CASCADE,
    order_discount_id  BIGINT NOT NULL
                       REFERENCES shopify.order_discounts (id) ON DELETE CASCADE,
    allocated_amount   NUMERIC(12,2) NOT NULL,
    currency           CHAR(3)
);

CREATE INDEX IF NOT EXISTS idx_allocations_line_item ON shopify.line_item_discount_allocations (line_item_id);

-- ----------------------------------------------------------------------------
-- sessions_daily — aggregate storefront traffic from Shopify Analytics
-- (ShopifyQL `sessions` dataset via shopifyqlQuery; see the session cell in
-- notebooks/shopify.ipynb). This is AGGREGATE data: there is no session id,
-- so it does not join to the order fact tables — it sits beside them for
-- traffic/conversion widgets (sessions vs orders per day).
-- Sync: upsert on (session_date, referrer_source); re-fetch the last few days
-- each night because Shopify keeps adjusting recent session counts.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shopify.sessions_daily (
    session_date     DATE NOT NULL,               -- day bucket (shop timezone, as ShopifyQL returns)
    referrer_source  TEXT NOT NULL,               -- social / direct / search / email / unknown
    sessions         INTEGER NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_date, referrer_source)
);

CREATE INDEX IF NOT EXISTS idx_sessions_daily_date ON shopify.sessions_daily (session_date);

-- ============================================================================
-- Dashboard convenience view — daily totals by channel & device, ready for
-- the FastAPI reports layer to SELECT from.
-- ============================================================================
CREATE OR REPLACE VIEW shopify.v_daily_sales_by_channel AS
SELECT
    (o.created_at AT TIME ZONE 'America/New_York')::date AS order_date,
    COALESCE(a.traffic_channel, 'UNKNOWN')               AS traffic_channel,
    COALESCE(a.traffic_source,  'UNKNOWN')               AS traffic_source,
    COALESCE(a.device_type,     'unknown')               AS device_type,
    COUNT(*)                                             AS orders,
    SUM(o.total_amount)                                  AS gross_revenue,
    SUM(o.total_refunded)                                AS refunded,
    SUM(o.net_payment)                                   AS net_revenue
FROM shopify.orders o
LEFT JOIN shopify.order_attribution a USING (order_id)
GROUP BY 1, 2, 3, 4;

-- Daily conversion — sessions vs orders, joined on the day bucket.
CREATE OR REPLACE VIEW shopify.v_daily_conversion AS
SELECT
    s.session_date                                             AS order_date,
    SUM(s.sessions)                                            AS sessions,
    COALESCE(o.orders, 0)                                      AS orders,
    o.net_revenue,
    ROUND(COALESCE(o.orders, 0)::numeric
          / NULLIF(SUM(s.sessions), 0) * 100, 2)               AS conversion_pct
FROM shopify.sessions_daily s
LEFT JOIN (
    SELECT (created_at AT TIME ZONE 'America/New_York')::date AS d,
           COUNT(*)                                           AS orders,
           SUM(net_payment)                                   AS net_revenue
    FROM shopify.orders
    GROUP BY 1
) o ON o.d = s.session_date
GROUP BY s.session_date, o.orders, o.net_revenue;

-- ============================================================================
-- v_net_sales_lines — THE definition of net sales, one row per event.
--
--     SUM(amount) over any slice of this view IS net sales for that slice.
--
-- One row per sold line (positive) and one per refunded line (negative), each
-- stamped with the date it books on: sales at the order's creation date,
-- returns at the REFUND's processed date. A refund therefore lands in the month
-- it happened, never back in the month of the original order.
--
-- Exists because three endpoints in api/dashboard.py each grew their own idea
-- of which lines count — no filter, `line_status = 'FULFILLED'`, and
-- `line_status <> 'REMOVED'` — and one of them subtracted refunds for lines it
-- had not counted as sold. Aggregate this view instead of re-deriving the rule.
-- Full reasoning, traps, and the reconciliation to Shopify's own Sales report:
-- docs/net-sales-definition.md. Runnable/parameterised twin with every toggle
-- exposed: db/queries/net_sales.sql.
--
-- Deliberate choices baked in here, both revisitable in one place:
--   * package protection EXCLUDED (x-redo / ROUTEINS*) — see §3 of the doc;
--     this is a known, intentional divergence from Shopify
--   * gift cards INCLUDED — Shopify excludes them, we do not (§8, open)
-- `line_status` is carried as a column, NOT filtered: dropping a status here
-- while still subtracting its refunds is exactly the bug this view retires.
--
-- Regex (!~) rather than LIKE so the text carries no '%' — schema.sql is
-- executed unparameterised today, but a stray '%' becomes a landmine the moment
-- anything runs it through psycopg2. Verified equivalent to
-- `NOT LIKE 'ROUTEINS%'` over all 236,487 line items (2026-07-31).
-- ============================================================================
CREATE OR REPLACE VIEW shopify.v_net_sales_lines AS
SELECT
    'SALE'::text                                         AS row_type,
    (o.created_at AT TIME ZONE 'America/New_York')::date AS date_key,
    o.order_id,
    o.order_name,
    li.line_item_id,
    li.sku,
    li.title,
    li.season_code,
    li.line_status,
    li.quantity                                          AS quantity,
    li.discounted_unit_price * li.quantity               AS amount,
    NULL::text                                           AS restock_type
FROM shopify.order_line_items li
JOIN shopify.orders o USING (order_id)
WHERE COALESCE(li.sku, '') <> 'x-redo'
  AND COALESCE(li.sku, '') !~ '^ROUTEINS'

UNION ALL

-- Inner JOIN to order_line_items (not LEFT): a refund line is excluded on the
-- same terms as the sale it reverses, so we never subtract a return for
-- something never counted as sold. Safe because every refund line has a
-- matching order line — guarded by tests/test_no_orphan_refund_lines.
SELECT
    'RETURN'::text,
    (rli.processed_at AT TIME ZONE 'America/New_York')::date,
    o.order_id,
    o.order_name,
    li.line_item_id,
    li.sku,
    li.title,
    li.season_code,
    li.line_status,
    -rli.quantity,
    -rli.subtotal,
    rli.restock_type
FROM shopify.refund_line_items rli
JOIN shopify.order_line_items li ON li.order_id     = rli.order_id
                                AND li.line_item_id = rli.line_item_id
JOIN shopify.orders o           ON o.order_id      = rli.order_id
WHERE COALESCE(li.sku, '') <> 'x-redo'
  AND COALESCE(li.sku, '') !~ '^ROUTEINS';

-- Note on indexes: both branches filter on the LOCAL date, which no plain index
-- on created_at / processed_at can serve, so this scans. That is not a
-- regression — api/dashboard.py's _IN_RANGE has always had the same shape and
-- is fast enough. Expression indexes on
-- ((created_at AT TIME ZONE 'America/New_York')::date) would make it sargable,
-- but CREATE INDEX takes a lock the nightly sync would have to wait behind, so
-- that is a deliberate follow-up rather than a free win bundled in here.

-- ============================================================================
-- Example upsert (parent) — the loader should follow this pattern:
--
-- INSERT INTO shopify.orders (order_id, order_name, created_at, ...)
-- VALUES (%s, %s, %s, ...)
-- ON CONFLICT (order_id) DO UPDATE SET
--     financial_status   = EXCLUDED.financial_status,
--     fulfillment_status = EXCLUDED.fulfillment_status,
--     total_amount       = EXCLUDED.total_amount,
--     synced_at          = now();
--
-- Children (discounts, line items, allocations): per order_id,
--   DELETE FROM shopify.order_discounts WHERE order_id = %s;  -- cascades not needed, then re-insert
-- ============================================================================

-- ============================================================================
-- GA4 traffic schema — session-level analytics Shopify's API can't provide
-- (docs/ga4-integration-plan.md). Fed by connectors/ga4_api.py via
-- reports/ga4_sync. All tables are daily aggregates, UPSERTed on their PK;
-- the nightly sync re-fetches the last ~3 days (GA4 revises recent data).
-- GA4 data starts 2023-02-06 (when tagging began) — earlier traffic exists
-- only in shopify.sessions_daily at coarser grain.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS ga4;

-- new vs returning visitors (boss items 1-2)
CREATE TABLE IF NOT EXISTS ga4.visitors_daily (
    session_date     DATE NOT NULL,
    new_vs_returning TEXT NOT NULL,               -- new / returning / unknown
    sessions         INTEGER NOT NULL DEFAULT 0,
    total_users      INTEGER NOT NULL DEFAULT 0,
    new_users        INTEGER NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_date, new_vs_returning)
);

-- traffic by channel/source/medium (boss item 3)
CREATE TABLE IF NOT EXISTS ga4.channel_daily (
    session_date  DATE NOT NULL,
    channel_group TEXT NOT NULL,                  -- GA4 Default Channel Grouping
    source        TEXT NOT NULL,                  -- Facebook, google, klaviyo, ...
    medium        TEXT NOT NULL,                  -- cpc, organic, email, ...
    sessions      INTEGER NOT NULL DEFAULT 0,
    total_users   INTEGER NOT NULL DEFAULT 0,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_date, channel_group, source, medium)
);

-- traffic by device (boss item 6 — the session-level version)
CREATE TABLE IF NOT EXISTS ga4.device_daily (
    session_date    DATE NOT NULL,
    device_category TEXT NOT NULL,                -- mobile / desktop / tablet / smart tv
    sessions        INTEGER NOT NULL DEFAULT 0,
    total_users     INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_date, device_category)
);

-- traffic by geography (boss item 8 — filter country = 'United States' for states)
CREATE TABLE IF NOT EXISTS ga4.region_daily (
    session_date DATE NOT NULL,
    country      TEXT NOT NULL,
    region       TEXT NOT NULL,                   -- state / province
    sessions     INTEGER NOT NULL DEFAULT 0,
    total_users  INTEGER NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_date, country, region)
);

-- landing page performance, GA4 view (boss item 7; Shopify's version is the cross-check)
CREATE TABLE IF NOT EXISTS ga4.landing_pages_daily (
    session_date     DATE NOT NULL,
    landing_page     TEXT NOT NULL,
    sessions         INTEGER NOT NULL DEFAULT 0,
    engaged_sessions INTEGER NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_date, landing_page)
);

CREATE INDEX IF NOT EXISTS idx_ga4_region_us
    ON ga4.region_daily (session_date, region) WHERE country = 'United States';

-- Dashboard views over GA4 traffic
CREATE OR REPLACE VIEW ga4.v_monthly_visitors AS
SELECT date_trunc('month', session_date)::date AS month,
       new_vs_returning,
       SUM(sessions)    AS sessions,
       SUM(total_users) AS users
FROM ga4.visitors_daily
GROUP BY 1, 2;

CREATE OR REPLACE VIEW ga4.v_monthly_channels AS
SELECT date_trunc('month', session_date)::date AS month,
       channel_group,
       SUM(sessions)    AS sessions,
       SUM(total_users) AS users
FROM ga4.channel_daily
GROUP BY 1, 2;

CREATE OR REPLACE VIEW ga4.v_us_states_monthly AS
SELECT date_trunc('month', session_date)::date AS month,
       region AS state,
       SUM(sessions)    AS sessions,
       SUM(total_users) AS users
FROM ga4.region_daily
WHERE country = 'United States'
GROUP BY 1, 2;

-- ----------------------------------------------------------------------------
-- Monthly conversion by traffic channel — GA4 sessions (denominator) joined
-- with Shopify orders (numerator) in GA4's channel vocabulary.
-- Orders are mapped via the corrected traffic_channel (see transform note
-- 2026-07-09: cpc+facebook = Paid Social, not Paid Search); GA4's
-- 'Paid Shopping'/'Cross-network' fold into Paid Search because order UTMs
-- can't distinguish shopping campaigns.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW ga4.v_monthly_channel_conversion AS
WITH s AS (
    SELECT date_trunc('month', session_date)::date AS month,
           CASE channel_group WHEN 'Paid Shopping' THEN 'Paid Search'
                              WHEN 'Cross-network' THEN 'Paid Search'
                              ELSE channel_group END AS channel,
           SUM(sessions) AS sessions
    FROM ga4.channel_daily
    GROUP BY 1, 2
),
o AS (
    SELECT date_trunc('month', created_at AT TIME ZONE 'America/New_York')::date AS month,
           CASE
             WHEN a.traffic_channel = 'Paid Social'                        THEN 'Paid Social'
             WHEN a.traffic_channel IN ('Paid Search','Paid Other','Paid') THEN 'Paid Search'
             WHEN a.traffic_channel = 'Email'                              THEN 'Email'
             WHEN a.traffic_channel IN ('SMS','Text')                      THEN 'SMS'
             WHEN a.traffic_channel = 'Seo'
                  OR LOWER(a.traffic_source) IN ('google','bing','yahoo','duckduckgo') THEN 'Organic Search'
             WHEN LOWER(a.traffic_source) = 'direct'                       THEN 'Direct'
             WHEN LOWER(a.traffic_source) IN ('facebook','instagram')      THEN 'Organic Social'
             ELSE 'Unassigned'
           END AS channel,
           COUNT(*)                AS orders,
           ROUND(SUM(net_payment)) AS net_revenue
    FROM shopify.orders
    LEFT JOIN shopify.order_attribution a USING (order_id)
    GROUP BY 1, 2
)
SELECT s.month,
       s.channel,
       s.sessions,
       COALESCE(o.orders, 0)                       AS orders,
       o.net_revenue,
       ROUND(o.net_revenue / NULLIF(o.orders, 0))  AS aov,
       ROUND(COALESCE(o.orders, 0)::numeric
             / NULLIF(s.sessions, 0) * 100, 2)     AS conversion_pct
FROM s
LEFT JOIN o USING (month, channel);


-- =====================
-- Judgeme reviews schema
-- =====================

CREATE SCHEMA IF NOT EXISTS judgeme;

CREATE TABLE IF NOT EXISTS judgeme.reviews (
    id                   BIGINT PRIMARY KEY,
    rating               SMALLINT,
    title                TEXT,
    body                 TEXT,
    created_at           TIMESTAMPTZ,
    updated_at           TIMESTAMPTZ,
    verified             TEXT,          -- e.g. 'verified-purchase' (string, not bool)
    published            BOOLEAN,
    curated              TEXT,
    hidden               BOOLEAN,
    featured             BOOLEAN,
    source               TEXT,
    product_external_id  BIGINT,
    product_handle       TEXT,
    product_title        TEXT,
    ip_address           TEXT,
    reviewer_id          BIGINT,
    reviewer_external_id BIGINT,
    reviewer_name        TEXT,
    reviewer_email       TEXT,
    has_pictures         BOOLEAN,
    has_videos           BOOLEAN,
    pictures             JSONB,         -- keep the rare (8) picture blobs as-is
    synced_at            TIMESTAMPTZ DEFAULT now()
);


-- ============================================================================
-- ads schema — paid ads performance (Meta + Pinterest), platform-reported
--
-- Daily grain, campaign level, one unified table (a third platform is just a
-- new `platform` value). purchases / purchase_value are the PLATFORMS'
-- self-attributed numbers (Meta pixel / Pinterest tag) — they can both claim
-- the same Shopify order, so cross-platform sums may exceed real orders.
-- Derived metrics (CTR/CPC/ROAS/CPA) live only in the view, never stored.
-- Design: docs/superpowers/specs/2026-07-13-ads-performance-schema-design.md
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS ads;

CREATE TABLE IF NOT EXISTS ads.campaign_daily (
    date             DATE NOT NULL,
    platform         TEXT NOT NULL,               -- 'meta' / 'pinterest'
    campaign_id      TEXT NOT NULL,               -- platform's stable id
    campaign_name    TEXT NOT NULL,               -- display name (can be renamed)
    status           TEXT,                        -- ACTIVE / PAUSED / ...
    spend            NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions      BIGINT  NOT NULL DEFAULT 0,
    clicks           INTEGER NOT NULL DEFAULT 0,
    purchases        INTEGER NOT NULL DEFAULT 0,  -- platform-attributed purchase count
    purchase_value   NUMERIC(12,2) NOT NULL DEFAULT 0,  -- platform-attributed revenue
    currency         TEXT NOT NULL DEFAULT 'USD',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, platform, campaign_id)
);

-- Upgrade path: rename pre-2026-07-13 columns in place
-- (no RENAME COLUMN IF EXISTS in Postgres, hence the DO block).
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'ads' AND table_name = 'campaign_daily'
                 AND column_name = 'conversions') THEN
        ALTER TABLE ads.campaign_daily RENAME COLUMN conversions TO purchases;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'ads' AND table_name = 'campaign_daily'
                 AND column_name = 'conversion_value') THEN
        ALTER TABLE ads.campaign_daily RENAME COLUMN conversion_value TO purchase_value;
    END IF;
END $$;

-- The monthly report: platform, month, campaign, raw sums + derived metrics.
-- NULLIF guards: zero-click / zero-spend periods yield NULL, not div-by-zero.
-- DROP first: CREATE OR REPLACE cannot rename view columns.
DROP VIEW IF EXISTS ads.v_campaign_monthly;
CREATE VIEW ads.v_campaign_monthly AS
SELECT
    platform,
    date_trunc('month', date)::date              AS month,
    campaign_id,
    max(campaign_name)                           AS campaign_name,  -- latest name wins
    sum(spend)                                   AS spend,
    sum(impressions)                             AS impressions,
    sum(clicks)                                  AS clicks,
    round(sum(clicks)::numeric / NULLIF(sum(impressions), 0) * 100, 2) AS ctr_pct,
    round(sum(spend) / NULLIF(sum(clicks), 0), 2)            AS cpc,
    sum(purchases)                               AS purchases,
    sum(purchase_value)                          AS revenue,
    round(sum(purchase_value) / NULLIF(sum(spend), 0), 2)    AS roas,
    round(sum(spend) / NULLIF(sum(purchases), 0), 2)         AS cpa
FROM ads.campaign_daily
GROUP BY platform, date_trunc('month', date), campaign_id;

-- ---------------------------------------------------------------------------
-- Ad-set / ad level (Meta only for now; platform column kept for symmetry
-- with campaign_daily). Facts mirror ads.campaign_daily; slowly-changing
-- attributes (targeting, creative) live in *_meta dimension tables refreshed
-- on every sync (upsert on (platform, id)).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ads.adset_daily (
    date             DATE NOT NULL,
    platform         TEXT NOT NULL,               -- 'meta'
    adset_id         TEXT NOT NULL,
    adset_name       TEXT NOT NULL,
    campaign_id      TEXT NOT NULL,
    campaign_name    TEXT NOT NULL,
    spend            NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions      BIGINT  NOT NULL DEFAULT 0,
    clicks           INTEGER NOT NULL DEFAULT 0,
    purchases        INTEGER NOT NULL DEFAULT 0,
    purchase_value   NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency         TEXT NOT NULL DEFAULT 'USD',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, platform, adset_id)
);

CREATE TABLE IF NOT EXISTS ads.ad_daily (
    date             DATE NOT NULL,
    platform         TEXT NOT NULL,               -- 'meta'
    ad_id            TEXT NOT NULL,
    ad_name          TEXT NOT NULL,
    adset_id         TEXT NOT NULL,
    adset_name       TEXT NOT NULL,
    campaign_id      TEXT NOT NULL,
    campaign_name    TEXT NOT NULL,
    spend            NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions      BIGINT  NOT NULL DEFAULT 0,
    clicks           INTEGER NOT NULL DEFAULT 0,
    purchases        INTEGER NOT NULL DEFAULT 0,
    purchase_value   NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency         TEXT NOT NULL DEFAULT 'USD',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, platform, ad_id)
);

-- Current targeting per ad set, classified for reporting. targeting_raw keeps
-- the full spec so the classification rule can evolve without a re-fetch.
CREATE TABLE IF NOT EXISTS ads.adset_meta (
    platform         TEXT NOT NULL,
    adset_id         TEXT NOT NULL,
    status           TEXT,                        -- effective_status
    targeting_type   TEXT,   -- advantage_plus | retargeting | lookalike | interest | broad
    lookalike_source TEXT,   -- origin audience name(s) when lookalikes are used
    audiences        TEXT,   -- included custom-audience names, comma-joined
    geo              TEXT,   -- e.g. 'US' or 'US, California'
    targeting_raw    JSONB,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (platform, adset_id)
);

-- ---------------------------------------------------------------------------
-- Dashboard login (api/auth.py). Roles: internal = every page; external =
-- Website Traffic / Marketing / Reviews only (enforced by API middleware).
-- Passwords are scrypt hashes; users are managed via `python -m api.users_cli`.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    email      TEXT PRIMARY KEY,
    pw_hash    TEXT NOT NULL,                 -- scrypt$n$r$p$salt_hex$hash_hex
    role       TEXT NOT NULL DEFAULT 'external'
               CHECK (role IN ('internal', 'external')),
    active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login TIMESTAMPTZ
);

-- Current creative attributes per ad. landing_url is NULL for catalog/dynamic
-- ads (template URLs like {{product.link}}) — is_dynamic marks those.
CREATE TABLE IF NOT EXISTS ads.ad_meta (
    platform         TEXT NOT NULL,
    ad_id            TEXT NOT NULL,
    status           TEXT,                        -- effective_status
    creative_id      TEXT,
    creative_format  TEXT,                        -- image | video | carousel | mixed | unknown
    landing_url      TEXT,
    is_dynamic       BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (platform, ad_id)
);
