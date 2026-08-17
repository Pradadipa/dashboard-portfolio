# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Business Dashboard: an e-commerce monitoring dashboard unifying Shopify, GA4, paid ads (Meta/Pinterest), and Judge.me reviews data.

- Backend: FastAPI + SQLAlchemy (async) + asyncpg, in `backend/`
- Database: PostgreSQL 16, schema in `db/schema.sql`
- Frontend: React + TypeScript + Tremor, in `frontend/` (not yet scaffolded)

Status: early development. Only the revenue-summary vertical slice (schema → service → schema model) exists so far; no API routes are wired up yet (`backend/app/api/` is an empty package).

## Commands

All backend commands run from `backend/` using `uv` (uv.lock is checked in).

```bash
cd backend
uv sync                     # install dependencies
uv run pytest               # run tests
uv run ruff check .         # lint
uv run python test_db.py       # sanity-check DB connectivity + shopify.v_net_sales_lines row counts
uv run python test_service.py  # exercise get_revenue_summary() against real data for a date range
```

There is no `uv run uvicorn app.main:...` yet — no FastAPI app entrypoint/router exists yet (see Architecture).

Database schema is applied by running `db/schema.sql` directly against the target Postgres database (e.g. `psql $DATABASE_URL -f db/schema.sql`); it is idempotent (`CREATE ... IF NOT EXISTS`, `CREATE OR REPLACE VIEW`) and safe to re-run.

Backend config comes from `backend/.env` (see `backend/.env.example`): `DATABASE_URL` (asyncpg DSN), `DEBUG`, `BUSINESS_TIMEZONE`.

## Architecture

### Backend layering

`backend/app/` follows a strict layer separation, each with its own `__init__.py` package:

- `core/config.py` — Pydantic `Settings` (from `.env`), exported as a singleton `settings`.
- `db/session.py` — async SQLAlchemy engine/session factory (`AsyncSessionLocal`) and the `get_db()` FastAPI dependency.
- `schemas/` — Pydantic response models (e.g. `RevenueSummary`). Monetary fields are always `Decimal`, never `float`.
- `services/` — business logic; takes an `AsyncSession` + params, runs raw SQL via `sqlalchemy.text()`, returns a schema model. Not ORM-mapped — the DB layer is schema.sql + hand-written SQL, not SQLAlchemy models/migrations.
- `api/` — intended for FastAPI routers; currently empty.

There's a stray `backend/src/backend/` package (uv project scaffold artifact) that isn't part of the real app — the app lives in `backend/app/`.

### The net-sales data model (`db/schema.sql`)

This is the most important thing to understand before touching revenue/sales logic. Four Postgres schemas:

- **`shopify`** — orders, customers, line items, discounts, refunds, and attribution, synced from Shopify's GraphQL Admin API (see comments atop `db/schema.sql` referencing `notebooks/shopify.ipynb`, which isn't in this repo yet).
- **`ga4`** — daily-aggregate traffic tables (visitors, channel, device, region, landing pages) fed by a GA4 connector; no session-level join key to Shopify, so it sits beside the fact tables for traffic/conversion widgets.
- **`ads`** — daily campaign/adset/ad performance from Meta + Pinterest, platform-self-attributed (can double-count the same Shopify order across platforms). Derived metrics (CTR, CPC, ROAS, CPA) are computed only in views (e.g. `ads.v_campaign_monthly`), never stored.
- **`judgeme`** — product reviews.
- **`auth`** — dashboard login users (scrypt-hashed passwords), with `internal`/`external` roles gating page access (external = Website Traffic / Marketing / Reviews only). No CLI for this exists yet in this repo despite the comment referencing `python -m api.users_cli`.

**`shopify.v_net_sales_lines` is the canonical net-sales definition** — every revenue/sales query should aggregate `SUM(amount)` over this view rather than re-deriving sales/returns logic against `orders`/`order_line_items`/`refund_line_items` directly (see the large comment block above it in `db/schema.sql` for the history of why: three endpoints previously each invented their own "which lines count" rule and one incorrectly subtracted refunds for lines never counted as sold). Key properties:

- One row per sold line item (`row_type = 'SALE'`, positive `amount`) and one row per refunded line (`row_type = 'RETURN'`, negative `amount`), each stamped with the date it books on — sales at order creation date, returns at the refund's `processed_at` date (in `America/New_York`, matching `BUSINESS_TIMEZONE`). A refund lands in the month it happened, not the original order's month.
- Package-protection line items (`sku = 'x-redo'` or `sku ~ '^ROUTEINS'`) are excluded from both branches.
- Refund lines join `order_line_items` with an **inner** join, not a left join — a refund is only counted if the line it reverses was counted as sold.

Other reconciliation subtlety: `shopify.refunds.total_refunded` (cash returned) and `shopify.refund_line_items.subtotal` (product value of named lines) measure different things and must not be netted against each other directly — refunds settled as store credit/gift card/exchange have `total_refunded = 0` even though goods came back. Use `shopify.v_refund_reconciliation` for that comparison, not ad hoc subtraction.

Deeper design rationale (when it exists) lives in `docs/net-sales-definition.md` and `docs/superpowers/specs/` — check there before changing revenue/refund logic; neither currently has content checked into this repo's `docs/` (empty at time of writing).

### Money handling convention

All monetary values flow through as `Decimal`, quantized to 2 decimal places at the service boundary (see `services/revenue_services.py`) — never `float`. Follow this pattern for any new revenue/spend calculation.
