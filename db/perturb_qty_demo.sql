-- ============================================================================
-- perturb_qty_demo.sql — decouple unit volume from the source. Run AFTER
-- perturb_demo.sql:
--
--   psql "$DEMO_URL" -v salt=yet-another-secret -f db/perturb_qty_demo.sql
--   docker compose exec -T db psql -U dashboard -d dashboard_demo \
--        -v salt=yet-another-secret -f /db/perturb_qty_demo.sql
--
-- perturb_demo.sql drops orders AND bumps line quantities; the two roughly
-- cancel out, so monthly Total QTY still lands within a few % of the source.
-- This script bumps single-unit lines to 2-4 units with a strength that varies
-- by month (~10-45% of eligible lines) and by product (0.5x-1.5x), so both the
-- monthly and the per-product unit curves stop tracking the source.
--
-- Money is held constant: unit prices are scaled by old_qty / new_qty, so each
-- line's value (and therefore net sales, order totals, refunds and customer
-- stats) only moves by rounding cents. Only lines with no refund, no return
-- and no partial removal are touched, so no refund can exceed its line.
--
-- Runs in ONE transaction; any failed check rolls everything back. Refuses to
-- run on a DB not named "demo", on one not perturbed first, or twice.
-- ============================================================================
\set ON_ERROR_STOP on
\if :{?salt}
\else
\set salt 'demo-qty-salt-change-me'
\endif

BEGIN;

DO $$
BEGIN
    IF current_database() !~* 'demo' THEN
        RAISE EXCEPTION 'Refusing to run: database "%" is not named like a demo copy (must contain "demo")', current_database();
    END IF;
    IF to_regclass('public.perturbation_log') IS NULL THEN
        RAISE EXCEPTION 'Run perturb_demo.sql first: this database is not perturbed';
    END IF;
    IF to_regclass('public.qty_perturbation_log') IS NOT NULL THEN
        RAISE EXCEPTION 'This database has already had its quantities perturbed';
    END IF;
END $$;

CREATE TEMP TABLE qpert_params AS SELECT :'salt'::text AS salt;

-- deterministic uniform [0,1) draw, seeded by the salt
CREATE FUNCTION pg_temp.qpert_u(t text) RETURNS numeric LANGUAGE sql AS $$
    SELECT ((hashtext(t || (SELECT salt FROM qpert_params))::bigint & 2147483647) % 10000) / 10000.0
$$;

CREATE TEMP TABLE qpert_before AS SELECT
    (SELECT SUM(quantity) FROM shopify.order_line_items)  AS units,
    (SELECT SUM(amount)   FROM shopify.v_net_sales_lines) AS net_sales;

-- ---------------------------------------------------------------------------
-- New quantity per eligible line. p = month strength x product factor.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE qpert_line AS
SELECT line_item_id, quantity AS old_q,
       CASE WHEN u >= p  THEN 1
            WHEN v < 0.70 THEN 2
            WHEN v < 0.92 THEN 3
            ELSE 4
       END AS new_q
FROM (
    SELECT li.line_item_id, li.quantity,
           LEAST(0.95,
                 (0.10 + 0.35 * pg_temp.qpert_u('m' || to_char(o.created_at AT TIME ZONE 'America/New_York', 'YYYY-MM')))
               * (0.50 + pg_temp.qpert_u('t' || li.title))) AS p,
           pg_temp.qpert_u('q' || li.line_item_id) AS u,
           pg_temp.qpert_u('s' || li.line_item_id) AS v
    FROM shopify.order_line_items li
    JOIN shopify.orders o USING (order_id)
    WHERE li.quantity = 1
      AND COALESCE(li.current_quantity, 0) = 1
      AND li.returned_quantity = 0
      AND COALESCE(li.original_unit_price, 0) > 0
      AND li.title IS NOT NULL
      AND COALESCE(li.sku, '') <> 'x-redo' AND COALESCE(li.sku, '') !~ '^ROUTEINS'
      AND NOT EXISTS (SELECT 1 FROM shopify.refund_line_items rli
                      WHERE rli.order_id = li.order_id AND rli.line_item_id = li.line_item_id)
) s;
DELETE FROM qpert_line WHERE new_q = old_q;
CREATE UNIQUE INDEX ON qpert_line (line_item_id);
ANALYZE qpert_line;

UPDATE shopify.order_line_items li SET
    original_unit_price      = ROUND(li.original_unit_price   * q.old_q / q.new_q, 2),
    discounted_unit_price    = ROUND(li.discounted_unit_price * q.old_q / q.new_q, 2),
    quantity                 = q.new_q,
    current_quantity         = q.new_q,
    unfulfilled_quantity     = CASE WHEN li.unfulfilled_quantity     = li.quantity THEN q.new_q
                                    ELSE li.unfulfilled_quantity END,
    non_fulfillable_quantity = CASE WHEN li.non_fulfillable_quantity = li.quantity THEN q.new_q
                                    ELSE li.non_fulfillable_quantity END
FROM qpert_line q
WHERE q.line_item_id = li.line_item_id;

-- ---------------------------------------------------------------------------
-- Verification — any failure raises and rolls the whole transaction back
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    b qpert_before%ROWTYPE;
    n bigint;
    units_now bigint;
    net_now numeric;
BEGIN
    SELECT * INTO b FROM qpert_before;
    SELECT SUM(quantity) INTO units_now FROM shopify.order_line_items;
    SELECT SUM(amount)   INTO net_now   FROM shopify.v_net_sales_lines;

    SELECT COUNT(*) INTO n FROM shopify.order_line_items WHERE quantity < 1 OR current_quantity > quantity;
    IF n > 0 THEN RAISE EXCEPTION '% line items have an invalid quantity', n; END IF;

    SELECT COUNT(*) INTO n
    FROM shopify.refund_line_items rli
    JOIN shopify.order_line_items li ON li.order_id = rli.order_id AND li.line_item_id = rli.line_item_id
    WHERE rli.quantity > li.quantity;
    IF n > 0 THEN RAISE EXCEPTION '% refund lines exceed their line quantity', n; END IF;

    SELECT COUNT(*) INTO n FROM shopify.order_line_items
    WHERE original_unit_price < 0 OR discounted_unit_price < 0 OR discounted_unit_price > original_unit_price;
    IF n > 0 THEN RAISE EXCEPTION '% line items have an inconsistent unit price', n; END IF;

    IF units_now < b.units * 1.05 THEN
        RAISE EXCEPTION 'units barely changed (% -> %)', b.units, units_now;
    END IF;
    IF abs(net_now - b.net_sales) > abs(b.net_sales) * 0.001 THEN
        RAISE EXCEPTION 'net sales drifted more than 0.1%% (% -> %)', b.net_sales, net_now;
    END IF;

    RAISE NOTICE 'lines changed: %', (SELECT COUNT(*) FROM qpert_line);
    RAISE NOTICE 'units:         % -> %', b.units, units_now;
    RAISE NOTICE 'net sales:     % -> %', b.net_sales, net_now;
END $$;

CREATE TABLE public.qty_perturbation_log AS SELECT now() AS applied_at;

COMMIT;

VACUUM ANALYZE shopify.order_line_items;
