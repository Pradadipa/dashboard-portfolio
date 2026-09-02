# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

## [Unreleased]

## [1.0.0] - 2026-09-02

Initial standard baseline: revenue-summary vertical slice end-to-end, from
Postgres schema through FastAPI service/endpoints to a working React
dashboard.

### Added

- Project scaffold: `db/schema.sql`, backend `uv` project, `CLAUDE.md`.
- Backend FastAPI app scaffold with layered `core/db/schemas/services/api`
  structure.
- `GET /api/revenue/summary` endpoint, backed by
  `shopify.v_net_sales_lines`.
- `GET /api/revenue/trend` endpoint for time-series revenue
  (`Granularity`, `RevenueTrendPoint`, `RevenueTrend` schemas).
- `GET /api/revenue/by-channel` endpoint (`ChannelRevenue`,
  `RevenueByChannel` schemas).
- Annotations API (create/list/get) with Alembic migrations.
- Frontend scaffold with Vite + React + TypeScript.
- Dashboard UI: `Header`, `DateRangePicker`, `GranularitySelector`,
  `KpiCard`/`KpiList`, `RevenueSummaryCards`, `RevenueTrendChart`,
  `RevenueByChannelChart`, wired to the backend revenue APIs.
- Tailwind CSS styling across the dashboard frontend.

### Fixed

- Channel revenue percentage now quantized to 2 decimal places.

[Unreleased]: https://github.com/Pradadipa/dashboard-portfolio/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Pradadipa/dashboard-portfolio/releases/tag/v1.0.0
