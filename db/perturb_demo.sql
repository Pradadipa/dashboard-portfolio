-- ============================================================================
-- perturb_demo.sql — make an ALREADY-ANONYMIZED demo DB structurally different
-- from the real one. anonymize_demo.sql only multiplies money by one constant,
-- so order counts, quantities and price ratios still mirror the source. This
-- script breaks that 1:1 fingerprint:
--
--   psql "$DEMO_URL" -v salt=another-secret -f db/perturb_demo.sql
--   docker compose exec -T db psql -U dashboard -d dashboard_demo \
--        -v salt=another-secret -f /db/perturb_demo.sql
--
--   1. orders     ~5-30% of orders dropped, with a rate that varies by month and
--                 by day, so the volume curve no longer matches the source
--   2. prices     each product gets its own price factor (0.70x-1.40x), snapped
--                 to a x.99 price point; discounts/allocations/refund lines
--                 follow the same factor
--   3. quantity   ~18% of untouched single-unit lines become 2-4 units
--   4. totals     order totals, refunds, discounts and customer lifetime stats
--                 are re-derived from the new lines so every view still adds up
--   5. numbering  order names are renumbered contiguously
--
-- Runs in ONE transaction; any failed check rolls everything back. Refuses to
-- run on a DB not named "demo", on one that was not anonymized first, or on one
-- already perturbed (a second run would compound the changes). ga4.* / ads.* are
-- left as they are. Never point it at production.
-- ============================================================================
\set ON_ERROR_STOP on
\if :{?salt}
\else
\set salt 'demo-perturb-salt-change-me'
\endif

BEGIN;

DO $$
BEGIN
    IF current_database() !~* 'demo' THEN
        RAISE EXCEPTION 'Refusing to run: database "%" is not named like a demo copy (must contain "demo")', current_database();
    END IF;
    IF to_regclass('public.anonymization_log') IS NULL THEN
        RAISE EXCEPTION 'Run anonymize_demo.sql first: this database is not anonymized';
    END IF;
    IF to_regclass('public.perturbation_log') IS NOT NULL THEN
        RAISE EXCEPTION 'This database has already been perturbed';
    END IF;
END $$;

CREATE TEMP TABLE pert_params AS SELECT :'salt'::text AS salt;

-- deterministic hash / uniform [0,1) draw, seeded by the salt
CREATE FUNCTION pg_temp.pert_h(t text) RETURNS bigint LANGUAGE sql AS $$
    SELECT (hashtext(t || (SELECT salt FROM pert_params))::bigint & 2147483647)
$$;
CREATE FUNCTION pg_temp.pert_u(t text) RETURNS numeric LANGUAGE sql AS $$
    SELECT (pg_temp.pert_h(t) % 10000) / 10000.0
$$;

CREATE TEMP TABLE pert_before AS SELECT
    (SELECT COUNT(*)                        FROM shopify.orders)           AS orders,
    (SELECT COUNT(*)                        FROM shopify.order_line_items) AS line_items,
    (SELECT SUM(quantity)                   FROM shopify.order_line_items) AS units,
    (SELECT SUM(amount)                     FROM shopify.v_net_sales_lines) AS net_sales;

-- ---------------------------------------------------------------------------
-- 1. Drop orders (children go with them via ON DELETE CASCADE)
-- ---------------------------------------------------------------------------
DELETE FROM shopify.orders o
WHERE pg_temp.pert_u('o' || o.order_id) <
      0.05
    + 0.20 * pg_temp.pert_u('m' || to_char(o.created_at AT TIME ZONE 'America/New_York', 'YYYY-MM'))
    + 0.10 * (pg_temp.pert_u('d' || (o.created_at AT TIME ZONE 'America/New_York')::date::text) - 0.5);

-- ---------------------------------------------------------------------------
-- 2 + 3. Per-line price ratio (r) and quantity multiplier (m).
-- Package-protection lines (x-redo / ROUTEINS*) are third-party: left alone.
-- Only lines with no returns/refunds/cancellation can gain units, so no refund
-- quantity can ever exceed the new line quantity.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE pert_price AS
SELECT title, 0.70 + 0.70 * pg_temp.pert_u('p' || title) AS f
FROM (SELECT DISTINCT title FROM shopify.order_line_items
      WHERE title IS NOT NULL
        AND COALESCE(sku, '') <> 'x-redo' AND COALESCE(sku, '') !~ '^ROUTEINS') t;
CREATE UNIQUE INDEX ON pert_price (title);

CREATE TEMP TABLE pert_line AS
SELECT s.line_item_id, s.order_id,
       s.old_net,
       CASE WHEN s.prot OR s.f IS NULL OR COALESCE(s.original_unit_price, 0) <= 0 THEN 1::numeric
            ELSE GREATEST(ROUND(s.original_unit_price * s.f) - 0.01, 0.99) / s.original_unit_price
       END AS r,
       CASE WHEN s.prot OR COALESCE(s.original_unit_price, 0) <= 0
                 OR s.quantity <> 1 OR COALESCE(s.current_quantity, 0) <> 1
                 OR s.returned_quantity > 0 OR s.has_refund THEN 1
            WHEN s.u < 0.12 THEN 2
            WHEN s.u < 0.16 THEN 3
            WHEN s.u < 0.18 THEN 4
            ELSE 1
       END AS m
FROM (
    SELECT li.line_item_id, li.order_id, li.quantity, li.current_quantity, li.returned_quantity,
           li.original_unit_price,
           li.discounted_unit_price * li.quantity AS old_net,
           (COALESCE(li.sku, '') = 'x-redo' OR COALESCE(li.sku, '') ~ '^ROUTEINS') AS prot,
           p.f,
           EXISTS (SELECT 1 FROM shopify.refund_line_items rli
                   WHERE rli.order_id = li.order_id AND rli.line_item_id = li.line_item_id) AS has_refund,
           pg_temp.pert_u('q' || li.line_item_id) AS u
    FROM shopify.order_line_items li
    LEFT JOIN pert_price p ON p.title = li.title
) s;
CREATE UNIQUE INDEX ON pert_line (line_item_id);
CREATE INDEX ON pert_line (order_id);
ANALYZE pert_line;

-- refunds: remember their old allocated value before line subtotals change
CREATE TEMP TABLE pert_refund AS
SELECT rf.refund_id, rf.order_id, rf.total_refunded AS old_total,
       COALESCE(SUM(rli.subtotal), 0) AS old_alloc
FROM shopify.refunds rf
LEFT JOIN shopify.refund_line_items rli ON rli.refund_id = rf.refund_id
GROUP BY rf.refund_id, rf.order_id, rf.total_refunded;
CREATE UNIQUE INDEX ON pert_refund (refund_id);

-- old order-level money, for the deltas applied below
CREATE TEMP TABLE pert_order AS
SELECT o.order_id, o.total_amount AS old_total, o.total_paid AS old_paid, o.total_refunded AS old_refunded,
       COALESCE(l.old_net, 0) AS old_net
FROM shopify.orders o
LEFT JOIN (SELECT order_id, SUM(old_net) AS old_net FROM pert_line GROUP BY order_id) l USING (order_id);
CREATE UNIQUE INDEX ON pert_order (order_id);

UPDATE shopify.order_line_items li SET
    original_unit_price      = ROUND(li.original_unit_price   * p.r, 2),
    discounted_unit_price    = ROUND(li.discounted_unit_price * p.r, 2),
    quantity                 = li.quantity * p.m,
    current_quantity         = li.current_quantity * p.m,
    unfulfilled_quantity     = li.unfulfilled_quantity * p.m,
    non_fulfillable_quantity = li.non_fulfillable_quantity * p.m
FROM pert_line p
WHERE p.line_item_id = li.line_item_id AND (p.r <> 1 OR p.m <> 1);

UPDATE shopify.line_item_discount_allocations a SET
    allocated_amount = ROUND(a.allocated_amount * p.r * p.m, 2)
FROM pert_line p
WHERE p.line_item_id = a.line_item_id AND (p.r <> 1 OR p.m <> 1);

UPDATE shopify.refund_line_items rli SET
    subtotal = ROUND(rli.subtotal * p.r, 2)
FROM pert_line p
WHERE p.line_item_id = rli.line_item_id AND p.order_id = rli.order_id AND p.r <> 1;

-- ---------------------------------------------------------------------------
-- 4. Re-derive order-level money from the new lines
-- ---------------------------------------------------------------------------
ALTER TABLE pert_order ADD COLUMN rho numeric;
UPDATE pert_order po SET rho = CASE WHEN po.old_net > 0 THEN l.new_net / po.old_net ELSE 1 END
FROM (SELECT order_id, SUM(discounted_unit_price * quantity) AS new_net
      FROM shopify.order_line_items GROUP BY order_id) l
WHERE l.order_id = po.order_id;
UPDATE pert_order SET rho = 1 WHERE rho IS NULL;

UPDATE shopify.order_discounts od SET
    value_amount = ROUND(od.value_amount * po.rho, 2)
FROM pert_order po
WHERE po.order_id = od.order_id AND od.value_amount IS NOT NULL;

-- refund cash follows the allocated line value; refunds that named no lines
-- follow the order-level ratio; zero-cash refunds (store credit) stay zero
UPDATE shopify.refunds rf SET
    total_refunded = CASE
        WHEN pr.old_total = 0  THEN 0
        WHEN pr.old_alloc > 0  THEN ROUND(pr.old_total * a.new_alloc / pr.old_alloc, 2)
        ELSE ROUND(pr.old_total * po.rho, 2) END
FROM pert_refund pr
JOIN pert_order po ON po.order_id = pr.order_id
LEFT JOIN (SELECT refund_id, SUM(subtotal) AS new_alloc
           FROM shopify.refund_line_items GROUP BY refund_id) a ON a.refund_id = pr.refund_id
WHERE pr.refund_id = rf.refund_id;

UPDATE shopify.orders o SET
    total_amount   = ROUND(o.total_amount * po.rho, 2),
    total_paid     = ROUND(o.total_paid   * po.rho, 2),
    total_refunded = GREATEST(o.total_refunded + COALESCE(d.delta, 0), 0),
    current_total  = GREATEST(o.current_total
                        + (ROUND(o.total_amount * po.rho, 2) - o.total_amount)
                        - COALESCE(d.delta, 0), 0),
    net_payment    = o.net_payment
                        + (ROUND(o.total_paid * po.rho, 2) - o.total_paid)
                        - COALESCE(d.delta, 0)
FROM pert_order po
LEFT JOIN (SELECT rf.order_id, SUM(rf.total_refunded - pr.old_total) AS delta
           FROM shopify.refunds rf JOIN pert_refund pr USING (refund_id)
           GROUP BY rf.order_id) d ON d.order_id = po.order_id
WHERE po.order_id = o.order_id;

-- customers: drop the ones left without orders, recompute lifetime stats
DELETE FROM shopify.customers c
WHERE NOT EXISTS (SELECT 1 FROM shopify.orders o WHERE o.customer_id = c.customer_id);

UPDATE shopify.customers c SET
    number_of_orders  = s.n,
    amount_spent      = s.spent,
    first_order_id    = s.first_id,
    first_purchase_at = s.first_at,
    last_order_id     = s.last_id,
    last_order_at     = s.last_at,
    customer_since    = LEAST(c.customer_since, s.first_at)
FROM (SELECT customer_id,
             COUNT(*)                                          AS n,
             SUM(net_payment)                                  AS spent,
             (array_agg(order_id   ORDER BY created_at ASC))[1]  AS first_id,
             MIN(created_at)                                   AS first_at,
             (array_agg(order_id   ORDER BY created_at DESC))[1] AS last_id,
             MAX(created_at)                                   AS last_at
      FROM shopify.orders GROUP BY customer_id) s
WHERE s.customer_id = c.customer_id;

-- ---------------------------------------------------------------------------
-- 5. Contiguous order numbering
-- ---------------------------------------------------------------------------
UPDATE shopify.orders o SET order_name = '#' || (10000 + r.rn)
FROM (SELECT order_id, row_number() OVER (ORDER BY created_at, order_id) AS rn FROM shopify.orders) r
WHERE r.order_id = o.order_id;

-- ---------------------------------------------------------------------------
-- Verification — any failure raises and rolls the whole transaction back
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    b pert_before%ROWTYPE;
    n bigint;
BEGIN
    SELECT * INTO b FROM pert_before;

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

    SELECT COUNT(*) INTO n FROM shopify.orders
    WHERE total_amount < 0 OR total_paid < 0 OR total_refunded < 0;
    IF n > 0 THEN RAISE EXCEPTION '% orders have negative money', n; END IF;

    IF (SELECT COUNT(*) FROM shopify.orders) = b.orders THEN RAISE EXCEPTION 'order count did not change'; END IF;
    IF (SELECT COUNT(*) FILTER (WHERE quantity > 1)::numeric / COUNT(*) FROM shopify.order_line_items) < 0.05 THEN
        RAISE EXCEPTION 'quantity distribution did not diversify';
    END IF;

    RAISE NOTICE 'orders:     % -> %', b.orders, (SELECT COUNT(*) FROM shopify.orders);
    RAISE NOTICE 'line items: % -> %', b.line_items, (SELECT COUNT(*) FROM shopify.order_line_items);
    RAISE NOTICE 'units:      % -> %', b.units, (SELECT SUM(quantity) FROM shopify.order_line_items);
    RAISE NOTICE 'net sales:  % -> %', b.net_sales, (SELECT SUM(amount) FROM shopify.v_net_sales_lines);
END $$;

CREATE TABLE public.perturbation_log AS SELECT now() AS applied_at;

COMMIT;

VACUUM ANALYZE;
