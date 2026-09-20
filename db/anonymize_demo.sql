-- ============================================================================
-- anonymize_demo.sql — turn a COPY of the real database into a demo dataset.
--
--   pg_dump "$PROD_URL" | psql "$DEMO_URL"        # 1. copy (DB name must contain "demo")
--   psql "$DEMO_URL" -v k=0.68 -v salt=my-secret \
--        -v brand='acme|acme co' -f db/anonymize_demo.sql   # 2. anonymize
--
--   k      money multiplier applied to EVERY monetary column (default 0.68)
--   salt   seeds all deterministic fake values; keep it private
--   brand  optional regex of real brand/company terms; the script scans every
--          text column afterwards and rolls back if any still match
--
-- Runs in ONE transaction: any failed check rolls everything back. Refuses to
-- run on a DB whose name lacks "demo", or on one already anonymized (a second
-- run would scale prices twice). Never point it at production.
-- ============================================================================
\set ON_ERROR_STOP on
\if :{?k}
\else
\set k 0.68
\endif
\if :{?salt}
\else
\set salt 'demo-salt-change-me'
\endif
\if :{?brand}
\else
\set brand ''
\endif

BEGIN;

DO $$
BEGIN
    IF current_database() !~* 'demo' THEN
        RAISE EXCEPTION 'Refusing to run: database "%" is not named like a demo copy (must contain "demo")', current_database();
    END IF;
    IF to_regclass('public.anonymization_log') IS NOT NULL THEN
        RAISE EXCEPTION 'This database has already been anonymized';
    END IF;
END $$;

CREATE TEMP TABLE anon_params AS
SELECT :k::numeric AS k, :'salt'::text AS salt, NULLIF(:'brand', '')::text AS brand;

DO $$
BEGIN
    IF (SELECT k FROM anon_params) NOT BETWEEN 0.1 AND 5 THEN
        RAISE EXCEPTION 'k must be between 0.1 and 5';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Baseline totals, used at the end to prove the transform stayed consistent
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE anon_before AS SELECT
    (SELECT SUM(amount)             FROM shopify.v_net_sales_lines)  AS net_sales,
    (SELECT SUM(net_payment)        FROM shopify.orders)             AS net_payment,
    (SELECT SUM(total_refunded)     FROM shopify.refunds)            AS refunds,
    (SELECT SUM(spend)              FROM ads.campaign_daily)         AS ad_spend,
    (SELECT SUM(purchase_value)     FROM ads.campaign_daily)         AS ad_revenue,
    (SELECT COUNT(*)                FROM shopify.orders)             AS orders,
    (SELECT COUNT(*)                FROM shopify.order_line_items)   AS line_items,
    (SELECT COUNT(*)                FROM judgeme.reviews)            AS reviews;

-- ---------------------------------------------------------------------------
-- Helpers (session-local, vanish on disconnect)
-- ---------------------------------------------------------------------------
CREATE FUNCTION pg_temp.anon_h(t text) RETURNS bigint LANGUAGE sql AS $$
    SELECT (hashtext(t || (SELECT salt FROM anon_params))::bigint & 2147483647)
$$;

CREATE FUNCTION pg_temp.anon_name(seed text) RETURNS text LANGUAGE sql AS $$
    SELECT f[1 + (h % cardinality(f))::int] || ' ' || l[1 + ((h / 97) % cardinality(l))::int]
    FROM (SELECT
            ARRAY['Ava','Liam','Noah','Emma','Olivia','Lucas','Mia','Ethan','Sofia','Mason',
                  'Isla','Logan','Zoe','Owen','Nora','Caleb','Layla','Wyatt','Chloe','Julian'] AS f,
            ARRAY['Carter','Bennett','Hayes','Morgan','Reed','Sullivan','Brooks','Foster','Ellis','Parker',
                  'Sawyer','Coleman','Harper','Griffin','Nash','Dawson','Quinn','Tucker','Vance','Whitman'] AS l,
            pg_temp.anon_h(seed) AS h) s
$$;

-- strips host + query string; product/collection slugs become opaque ids
CREATE FUNCTION pg_temp.anon_path(u text) RETURNS text LANGUAGE sql AS $$
    SELECT CASE
        WHEN u IS NULL THEN NULL
        WHEN p.path ~ '^/products/'    THEN '/products/item-' || lpad((pg_temp.anon_h(p.path) % 100000)::text, 5, '0')
        WHEN p.path ~ '^/collections/' THEN '/collections/collection-' || lpad((pg_temp.anon_h(p.path) % 1000)::text, 3, '0')
        WHEN p.path = '' THEN '/'
        ELSE p.path
    END
    FROM (SELECT regexp_replace(regexp_replace(u, '^https?://[^/]+', ''), '[?#].*$', '') AS path) p
$$;

-- ---------------------------------------------------------------------------
-- Mapping tables (real value -> fake value, consistent across all tables)
-- Package-protection lines (x-redo / ROUTEINS*) are third-party items and are
-- left untouched apart from price scaling.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE anon_product AS
WITH t AS (
    SELECT title AS orig FROM shopify.order_line_items
    WHERE title IS NOT NULL
      AND COALESCE(sku, '') <> 'x-redo' AND COALESCE(sku, '') !~ '^ROUTEINS'
    UNION
    SELECT product_title FROM judgeme.reviews WHERE product_title IS NOT NULL
), r AS (
    SELECT orig, (row_number() OVER (ORDER BY pg_temp.anon_h(orig), orig))::int AS n FROM t
), w AS (
    SELECT ARRAY['Classic','Everyday','Heritage','Coastal','Urban','Alpine','Cedar','Ember','Willow','Harbor',
                 'Summit','Meadow','Ridge','Sterling','Maple','Slate','Juniper','Aurora','Copper','Fable'] AS adj,
           ARRAY['Tote','Jacket','Hoodie','Scarf','Beanie','Sneaker','Backpack','Crewneck','Cardigan','Parka',
                 'Tee','Joggers','Boots','Vest','Blanket','Cap','Pouch','Sandal','Overshirt','Duffel',
                 'Shorts','Wallet','Mittens','Robe','Slipper'] AS noun
), nm AS (
    SELECT r.orig AS orig_title, r.n,
           w.adj[(r.n - 1) % cardinality(w.adj) + 1] || ' ' ||
           w.noun[((r.n - 1) / cardinality(w.adj)) % cardinality(w.noun) + 1] ||
           CASE WHEN r.n > cardinality(w.adj) * cardinality(w.noun)
                THEN ' ' || ((r.n - 1) / (cardinality(w.adj) * cardinality(w.noun)) + 1)::text
                ELSE '' END AS new_title
    FROM r CROSS JOIN w
)
SELECT orig_title, n, new_title,
       lower(regexp_replace(new_title, '[^a-zA-Z0-9]+', '-', 'g')) AS new_handle
FROM nm;
CREATE UNIQUE INDEX ON anon_product (orig_title);

CREATE TEMP TABLE anon_season AS
SELECT season_code AS orig,
       'S' || lpad((row_number() OVER (ORDER BY season_code))::text, 2, '0') AS alias
FROM (SELECT DISTINCT season_code FROM shopify.order_line_items WHERE season_code IS NOT NULL) s;
CREATE UNIQUE INDEX ON anon_season (orig);

CREATE TEMP TABLE anon_sku AS
SELECT s.sku AS orig_sku,
       COALESCE(a.alias, 'GEN') || '-' ||
       lpad((row_number() OVER (ORDER BY pg_temp.anon_h(s.sku), s.sku))::text, 5, '0') AS new_sku
FROM (SELECT sku, max(season_code) AS season_code
      FROM shopify.order_line_items
      WHERE sku IS NOT NULL AND sku <> '' AND sku <> 'x-redo' AND sku !~ '^ROUTEINS'
      GROUP BY sku) s
LEFT JOIN anon_season a ON a.orig = s.season_code;
CREATE UNIQUE INDEX ON anon_sku (orig_sku);

CREATE TEMP TABLE anon_discount AS
SELECT orig, 'PROMO' || lpad((row_number() OVER (ORDER BY pg_temp.anon_h(orig), orig))::text, 3, '0') AS new_code
FROM (SELECT lower(btrim(discount_code)) AS orig FROM shopify.orders
      WHERE btrim(COALESCE(discount_code, '')) <> ''
      UNION
      SELECT lower(btrim(code_or_title)) FROM shopify.order_discounts
      WHERE btrim(COALESCE(code_or_title, '')) <> '') s;
CREATE UNIQUE INDEX ON anon_discount (orig);

CREATE TEMP TABLE anon_utm AS
SELECT utm_campaign AS orig,
       'campaign-' || lpad((row_number() OVER (ORDER BY pg_temp.anon_h(utm_campaign), utm_campaign))::text, 3, '0') AS new_val
FROM (SELECT DISTINCT utm_campaign FROM shopify.order_attribution WHERE utm_campaign IS NOT NULL) s;
CREATE UNIQUE INDEX ON anon_utm (orig);

-- New ids use a text prefix so they can never collide with real (numeric) ids
-- while primary keys are rewritten row by row.
CREATE TEMP TABLE anon_campaign AS
SELECT orig_id, 'cmp_' || lpad(n::text, 4, '0') AS new_id,
       (ARRAY['Prospecting','Retargeting','Catalog Sales','Brand Awareness','Seasonal Promo'])[(n - 1) % 5 + 1]
           || ' ' || lpad(n::text, 2, '0') AS new_name
FROM (SELECT campaign_id AS orig_id, (row_number() OVER (ORDER BY pg_temp.anon_h(campaign_id), campaign_id))::int AS n
      FROM (SELECT campaign_id FROM ads.campaign_daily
            UNION SELECT campaign_id FROM ads.adset_daily
            UNION SELECT campaign_id FROM ads.ad_daily) u) s;
CREATE UNIQUE INDEX ON anon_campaign (orig_id);

CREATE TEMP TABLE anon_adset AS
SELECT orig_id, 'as_' || lpad(n::text, 5, '0') AS new_id, 'Ad Set ' || lpad(n::text, 3, '0') AS new_name
FROM (SELECT adset_id AS orig_id, (row_number() OVER (ORDER BY pg_temp.anon_h(adset_id), adset_id))::int AS n
      FROM (SELECT adset_id FROM ads.adset_daily
            UNION SELECT adset_id FROM ads.ad_daily
            UNION SELECT adset_id FROM ads.adset_meta) u) s;
CREATE UNIQUE INDEX ON anon_adset (orig_id);

CREATE TEMP TABLE anon_ad AS
SELECT orig_id, 'ad_' || lpad(n::text, 5, '0') AS new_id, 'Creative ' || lpad(n::text, 4, '0') AS new_name
FROM (SELECT ad_id AS orig_id, (row_number() OVER (ORDER BY pg_temp.anon_h(ad_id), ad_id))::int AS n
      FROM (SELECT ad_id FROM ads.ad_daily
            UNION SELECT ad_id FROM ads.ad_meta) u) s;
CREATE UNIQUE INDEX ON anon_ad (orig_id);

ANALYZE anon_product; ANALYZE anon_sku; ANALYZE anon_season; ANALYZE anon_discount;

-- ---------------------------------------------------------------------------
-- shopify.*  (money x k everywhere so views still reconcile)
-- ---------------------------------------------------------------------------
UPDATE shopify.customers SET
    email        = CASE WHEN email IS NULL THEN NULL
                        ELSE 'customer' || substr(md5(customer_id::text || (SELECT salt FROM anon_params)), 1, 12) || '@example.com' END,
    display_name = CASE WHEN display_name IS NULL THEN NULL ELSE pg_temp.anon_name(customer_id::text) END,
    amount_spent = ROUND(amount_spent * :k, 2),
    zip          = CASE WHEN zip IS NULL THEN NULL ELSE left(zip, 3) || '00' END,
    tags         = NULL;

UPDATE shopify.orders o SET
    order_name     = '#' || (10000 + r.rn),
    total_amount   = ROUND(o.total_amount   * :k, 2),
    current_total  = ROUND(o.current_total  * :k, 2),
    total_paid     = ROUND(o.total_paid     * :k, 2),
    total_refunded = ROUND(o.total_refunded * :k, 2),
    net_payment    = ROUND(o.net_payment    * :k, 2),
    discount_code  = (SELECT d.new_code FROM anon_discount d WHERE d.orig = lower(btrim(o.discount_code)))
FROM (SELECT order_id, row_number() OVER (ORDER BY created_at, order_id) AS rn FROM shopify.orders) r
WHERE r.order_id = o.order_id;

UPDATE shopify.order_attribution a SET
    user_agent   = NULL,
    referrer_url = CASE
        WHEN a.referrer_url IS NULL THEN NULL
        WHEN (SELECT p.brand FROM anon_params p) IS NOT NULL
             AND a.referrer_url ~* (SELECT p.brand FROM anon_params p) THEN NULL
        ELSE substring(a.referrer_url from '^https?://[^/?#]+') END,
    landing_page = pg_temp.anon_path(a.landing_page),
    utm_campaign = (SELECT u.new_val FROM anon_utm u WHERE u.orig = a.utm_campaign),
    utm_content  = NULL,
    utm_term     = NULL;

UPDATE shopify.order_discounts SET
    value_amount = ROUND(value_amount * :k, 2),
    description  = CASE WHEN description IS NULL THEN NULL ELSE 'Manual discount' END;

UPDATE shopify.order_discounts od SET code_or_title = d.new_code
FROM anon_discount d WHERE d.orig = lower(btrim(od.code_or_title));

UPDATE shopify.order_line_items li SET
    original_unit_price   = ROUND(li.original_unit_price   * :k, 2),
    discounted_unit_price = ROUND(li.discounted_unit_price * :k, 2),
    title = CASE WHEN COALESCE(li.sku, '') = 'x-redo' OR COALESCE(li.sku, '') ~ '^ROUTEINS' THEN li.title
                 ELSE (SELECT p.new_title FROM anon_product p WHERE p.orig_title = li.title) END,
    sku   = CASE WHEN COALESCE(li.sku, '') = 'x-redo' OR COALESCE(li.sku, '') ~ '^ROUTEINS' THEN li.sku
                 ELSE (SELECT s.new_sku FROM anon_sku s WHERE s.orig_sku = li.sku) END,
    season_code = (SELECT a.alias FROM anon_season a WHERE a.orig = li.season_code);

UPDATE shopify.line_item_discount_allocations SET allocated_amount = ROUND(allocated_amount * :k, 2);
UPDATE shopify.refund_line_items SET subtotal = ROUND(subtotal * :k, 2);
UPDATE shopify.refunds SET
    total_refunded = ROUND(total_refunded * :k, 2),
    note = CASE WHEN note IS NULL THEN NULL
                WHEN note ~* 'redo' THEN 'Return via app'
                ELSE 'Refund' END;

-- ---------------------------------------------------------------------------
-- ga4.* — only landing pages carry identifying text. Anonymised paths can
-- merge, so the table is rebuilt aggregated to respect its primary key.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE anon_lp AS
SELECT session_date, pg_temp.anon_path(landing_page) AS landing_page,
       SUM(sessions)::int AS sessions, SUM(engaged_sessions)::int AS engaged_sessions
FROM ga4.landing_pages_daily GROUP BY 1, 2;
TRUNCATE ga4.landing_pages_daily;
INSERT INTO ga4.landing_pages_daily (session_date, landing_page, sessions, engaged_sessions)
SELECT session_date, landing_page, sessions, engaged_sessions FROM anon_lp;

-- ---------------------------------------------------------------------------
-- ads.* — spend / revenue x k (ROAS unchanged); counts left as-is
-- ---------------------------------------------------------------------------
UPDATE ads.campaign_daily c SET
    campaign_id = m.new_id, campaign_name = m.new_name,
    spend = ROUND(c.spend * :k, 2), purchase_value = ROUND(c.purchase_value * :k, 2)
FROM anon_campaign m WHERE m.orig_id = c.campaign_id;

UPDATE ads.adset_daily d SET
    campaign_id = c.new_id, campaign_name = c.new_name,
    adset_id = s.new_id, adset_name = s.new_name,
    spend = ROUND(d.spend * :k, 2), purchase_value = ROUND(d.purchase_value * :k, 2)
FROM anon_campaign c, anon_adset s
WHERE c.orig_id = d.campaign_id AND s.orig_id = d.adset_id;

UPDATE ads.ad_daily d SET
    campaign_id = c.new_id, campaign_name = c.new_name,
    adset_id = s.new_id, adset_name = s.new_name,
    ad_id = a.new_id, ad_name = a.new_name,
    spend = ROUND(d.spend * :k, 2), purchase_value = ROUND(d.purchase_value * :k, 2)
FROM anon_campaign c, anon_adset s, anon_ad a
WHERE c.orig_id = d.campaign_id AND s.orig_id = d.adset_id AND a.orig_id = d.ad_id;

UPDATE ads.adset_meta m SET
    adset_id         = s.new_id,
    lookalike_source = CASE WHEN m.lookalike_source IS NULL THEN NULL ELSE 'Source audience' END,
    audiences        = CASE WHEN m.audiences IS NULL THEN NULL ELSE 'Custom audience' END,
    targeting_raw    = NULL
FROM anon_adset s WHERE s.orig_id = m.adset_id;

UPDATE ads.ad_meta m SET
    ad_id       = a.new_id,
    creative_id = CASE WHEN m.creative_id IS NULL THEN NULL ELSE 'crv_' || pg_temp.anon_h(m.creative_id)::text END,
    landing_url = pg_temp.anon_path(m.landing_url)
FROM anon_ad a WHERE a.orig_id = m.ad_id;

-- ---------------------------------------------------------------------------
-- judgeme.reviews — free text and reviewer identity replaced wholesale
-- ---------------------------------------------------------------------------
UPDATE judgeme.reviews r SET
    title = CASE
        WHEN COALESCE(r.rating, 3) >= 4 THEN (ARRAY['Love it','Great quality','Exactly what I wanted','Highly recommend'])[1 + (pg_temp.anon_h(r.id::text) % 4)::int]
        WHEN COALESCE(r.rating, 3) = 3  THEN (ARRAY['It is okay','Decent for the price','Average'])[1 + (pg_temp.anon_h(r.id::text) % 3)::int]
        ELSE (ARRAY['Not what I expected','Disappointed','Would not buy again'])[1 + (pg_temp.anon_h(r.id::text) % 3)::int] END,
    body = CASE
        WHEN COALESCE(r.rating, 3) >= 4 THEN (ARRAY['Great quality and fits perfectly. Would buy again.','Very comfortable and well made, arrived quickly.','Looks even better in person. Happy with this purchase.'])[1 + (pg_temp.anon_h(r.id::text) % 3)::int]
        WHEN COALESCE(r.rating, 3) = 3  THEN (ARRAY['Nice enough, though sizing runs a bit small.','Does the job. Material could be a little better.','Average quality for the price.'])[1 + (pg_temp.anon_h(r.id::text) % 3)::int]
        ELSE (ARRAY['Quality was lower than I hoped for.','Did not fit well and the material feels thin.','Arrived with a defect, disappointed overall.'])[1 + (pg_temp.anon_h(r.id::text) % 3)::int] END,
    product_external_id  = (SELECT 9000000000 + p.n FROM anon_product p WHERE p.orig_title = r.product_title),
    product_handle       = (SELECT p.new_handle    FROM anon_product p WHERE p.orig_title = r.product_title),
    product_title        = (SELECT p.new_title     FROM anon_product p WHERE p.orig_title = r.product_title),
    ip_address           = NULL,
    reviewer_id          = CASE WHEN r.reviewer_id IS NULL THEN NULL ELSE pg_temp.anon_h('rv' || r.reviewer_id::text) END,
    reviewer_external_id = CASE WHEN r.reviewer_external_id IS NULL THEN NULL ELSE pg_temp.anon_h('rx' || r.reviewer_external_id::text) END,
    reviewer_name        = CASE WHEN r.reviewer_name IS NULL THEN NULL
                                ELSE regexp_replace(pg_temp.anon_name('r' || r.id::text), ' (.)\S*$', ' \1.') END,
    reviewer_email       = CASE WHEN r.reviewer_email IS NULL THEN NULL
                                ELSE 'reviewer' || substr(md5(r.id::text || (SELECT salt FROM anon_params)), 1, 12) || '@example.com' END,
    has_pictures = FALSE,
    has_videos   = FALSE,
    pictures     = NULL;

-- ---------------------------------------------------------------------------
-- auth.users — real logins must not ship; create a demo user afterwards
-- ---------------------------------------------------------------------------
TRUNCATE auth.users;

-- ---------------------------------------------------------------------------
-- Verification — any failure raises and rolls the whole transaction back
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_k   numeric := (SELECT p.k FROM anon_params p);
    b     anon_before%ROWTYPE;
    n     bigint;
    chk   record;
BEGIN
    SELECT * INTO b FROM anon_before;

    FOR chk IN
        SELECT 'net_sales' AS name, b.net_sales AS before_v, (SELECT SUM(amount) FROM shopify.v_net_sales_lines) AS after_v
        UNION ALL SELECT 'net_payment', b.net_payment, (SELECT SUM(net_payment) FROM shopify.orders)
        UNION ALL SELECT 'refunds',     b.refunds,     (SELECT SUM(total_refunded) FROM shopify.refunds)
        UNION ALL SELECT 'ad_spend',    b.ad_spend,    (SELECT SUM(spend) FROM ads.campaign_daily)
        UNION ALL SELECT 'ad_revenue',  b.ad_revenue,  (SELECT SUM(purchase_value) FROM ads.campaign_daily)
    LOOP
        IF chk.before_v IS NOT NULL AND chk.before_v <> 0
           AND abs(chk.after_v / chk.before_v - v_k) / v_k > 0.005 THEN
            RAISE EXCEPTION 'Check failed for %: before=% after=% expected ratio %', chk.name, chk.before_v, chk.after_v, v_k;
        END IF;
        RAISE NOTICE 'ok  %: % -> % (ratio %)', chk.name, chk.before_v, chk.after_v,
                     CASE WHEN chk.before_v = 0 THEN NULL ELSE round(chk.after_v / chk.before_v, 4) END;
    END LOOP;

    IF (SELECT COUNT(*) FROM shopify.orders)           <> b.orders     THEN RAISE EXCEPTION 'order count changed'; END IF;
    IF (SELECT COUNT(*) FROM shopify.order_line_items) <> b.line_items THEN RAISE EXCEPTION 'line item count changed'; END IF;
    IF (SELECT COUNT(*) FROM judgeme.reviews)          <> b.reviews    THEN RAISE EXCEPTION 'review count changed'; END IF;

    SELECT COUNT(*) INTO n FROM shopify.customers WHERE email IS NOT NULL AND email !~ '@example\.com$';
    IF n > 0 THEN RAISE EXCEPTION '% customer emails were not anonymized', n; END IF;
    SELECT COUNT(*) INTO n FROM judgeme.reviews WHERE reviewer_email IS NOT NULL AND reviewer_email !~ '@example\.com$';
    IF n > 0 THEN RAISE EXCEPTION '% reviewer emails were not anonymized', n; END IF;
END $$;

-- Brand-term scan over every text/json column of the data schemas
DO $$
DECLARE
    v_brand text := (SELECT p.brand FROM anon_params p);
    c       record;
    n       bigint;
    hits    text[] := '{}';
BEGIN
    IF v_brand IS NULL THEN
        RAISE NOTICE 'brand scan skipped (pass -v brand=''term1|term2'' to enable)';
        RETURN;
    END IF;
    FOR c IN
        SELECT col.table_schema AS s, col.table_name AS t, col.column_name AS c
        FROM information_schema.columns col
        JOIN information_schema.tables tb
          ON tb.table_schema = col.table_schema AND tb.table_name = col.table_name
        WHERE tb.table_type = 'BASE TABLE'
          AND col.table_schema IN ('shopify', 'ga4', 'ads', 'judgeme')
          AND col.data_type IN ('text', 'character varying', 'character', 'json', 'jsonb')
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I.%I WHERE %I::text ~* %L', c.s, c.t, c.c, v_brand) INTO n;
        IF n > 0 THEN hits := hits || format('%s.%s.%s (%s rows)', c.s, c.t, c.c, n); END IF;
    END LOOP;
    IF cardinality(hits) > 0 THEN
        RAISE EXCEPTION 'Brand terms still present in: %', array_to_string(hits, ', ');
    END IF;
    RAISE NOTICE 'brand scan clean';
END $$;

CREATE TABLE public.anonymization_log AS
SELECT now() AS applied_at, k AS scale FROM anon_params;

COMMIT;

VACUUM ANALYZE;
