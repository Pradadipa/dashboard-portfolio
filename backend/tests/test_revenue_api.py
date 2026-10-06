"""
HTTP-level tests for /api/revenue/*.

The service tests already check the maths. These tests check what the FRONTEND relies on:
status codes, validation, and the shape of the JSON.
"""

from decimal import Decimal

import pytest

from tests.factories import add_line, add_order, utc

REVENUE_ENDPOINTS = ["/api/revenue/summary", "/api/revenue/trend", "/api/revenue/by-channel"]


async def test_health_check(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --------------------------------------------------------------------------- summary


async def test_summary_returns_expected_json(client, january_2026):
    response = await client.get(
        "/api/revenue/summary", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["net_sales"] == "190.00"
    assert body["total_sales"] == "240.00"
    assert body["total_returns"] == "50.00"
    assert body["total_orders"] == 3
    assert body["average_order_value"] == "63.33"
    assert body["net_sales_change_percent"] == "90.00"
    assert body["total_returns_change_percent"] is None
    assert body["net_sales_sparkline"][0] == {"date": "2026-01-10", "value": "180.00"}


async def test_summary_money_is_serialized_as_string_not_float(client, january_2026):
    """Project rule: money is Decimal end to end. A JSON float would reintroduce rounding drift."""
    response = await client.get(
        "/api/revenue/summary", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    body = response.json()
    for field in ("net_sales", "total_sales", "total_returns", "average_order_value"):
        assert isinstance(body[field], str), f"{field} must be a string, got {body[field]!r}"


# --------------------------------------------------------------------------- trend


async def test_trend_by_day(client, january_2026):
    response = await client.get(
        "/api/revenue/trend",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31", "granularity": "day"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_points"] == 3
    assert [p["date"] for p in body["data_points"]] == ["2026-01-10", "2026-01-15", "2026-01-20"]
    assert [p["current_net_sales"] for p in body["data_points"]] == ["180.00", "60.00", "-50.00"]
    assert body["current_total_net_sales"] == "190.00"


async def test_trend_by_month_collapses_to_one_point(client, january_2026):
    response = await client.get(
        "/api/revenue/trend",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31", "granularity": "month"},
    )

    body = response.json()
    assert body["total_points"] == 1
    assert body["data_points"][0]["date"] == "2026-01-01"
    assert body["data_points"][0]["current_net_sales"] == "190.00"
    assert body["data_points"][0]["current_orders"] == 3


async def test_trend_compares_with_same_day_last_year(client, db):
    await add_order(db, 1, utc(2025, 1, 10), net_payment="100.00")
    await add_order(db, 2, utc(2026, 1, 10), net_payment="150.00")
    # trend reads line items through v_net_sales_lines, so give both orders a line
    await add_line(db, 1, 1, "SKU-A", 1, "100.00")
    await add_line(db, 2, 2, "SKU-A", 1, "150.00")

    response = await client.get(
        "/api/revenue/trend",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31", "granularity": "day"},
    )

    point = response.json()["data_points"][0]
    assert point["current_net_sales"] == "150.00"
    assert point["previous_net_sales"] == "100.00"
    assert point["net_sales_change_percent"] == "50.00"


async def test_trend_without_last_year_data_has_no_growth_rate(client, january_2026):
    response = await client.get(
        "/api/revenue/trend", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    body = response.json()
    assert body["previous_total_net_sales"] == "0.00"
    assert body["net_sales_change_percent"] is None


async def test_trend_rejects_unknown_granularity(client):
    response = await client.get("/api/revenue/trend", params={"granularity": "decade"})

    assert response.status_code == 422


# --------------------------------------------------------------------------- by channel


async def _seed_channels(db, revenue_by_channel: dict[str, str]) -> None:
    for order_id, (channel, revenue) in enumerate(revenue_by_channel.items(), start=1):
        await add_order(db, order_id, utc(2026, 1, 5), net_payment=revenue, channel=channel)


async def test_by_channel_sorts_by_revenue_and_computes_share(client, db):
    await add_order(db, 1, utc(2026, 1, 5), net_payment="400.00", channel="Paid Social")
    await add_order(db, 2, utc(2026, 1, 6), net_payment="200.00", channel="Paid Social")
    await add_order(db, 3, utc(2026, 1, 7), net_payment="300.00", channel="Organic Search")
    await add_order(db, 4, utc(2026, 1, 8), net_payment="100.00", channel="Direct")

    response = await client.get(
        "/api/revenue/by-channel", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    body = response.json()
    assert [(c["channel"], c["revenue"], c["orders"], c["percentage"]) for c in body["channels"]] == [
        ("Paid Social", "600.00", 2, "60.00"),
        ("Organic Search", "300.00", 1, "30.00"),
        ("Direct", "100.00", 1, "10.00"),
    ]
    assert body["total_revenue"] == "1000.00"
    assert body["total_order"] == 4


async def test_by_channel_groups_everything_after_the_top_four_as_other(client, db):
    await _seed_channels(
        db,
        {
            "Ch1": "600.00",
            "Ch2": "500.00",
            "Ch3": "400.00",
            "Ch4": "300.00",
            "Ch5": "150.00",
            "Ch6": "50.00",
        },
    )

    response = await client.get(
        "/api/revenue/by-channel", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    channels = response.json()["channels"]
    assert [c["channel"] for c in channels] == ["Ch1", "Ch2", "Ch3", "Ch4", "Other"]
    assert channels[-1]["revenue"] == "200.00"  # Ch5 + Ch6


async def test_by_channel_limit_trims_the_list_but_not_the_total(client, db):
    await _seed_channels(db, {"Ch1": "600.00", "Ch2": "300.00", "Ch3": "100.00"})

    response = await client.get(
        "/api/revenue/by-channel",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31", "limit": 2},
    )

    body = response.json()
    assert [c["channel"] for c in body["channels"]] == ["Ch1", "Ch2"]
    assert body["total_revenue"] == "1000.00"  # still counts every channel
    assert body["channels"][0]["percentage"] == "60.00"  # share of the full total


@pytest.mark.parametrize("limit", [0, 51])
async def test_by_channel_limit_must_be_between_1_and_50(client, limit):
    response = await client.get("/api/revenue/by-channel", params={"limit": limit})

    assert response.status_code == 422


async def test_by_channel_with_no_orders_in_range_is_empty_not_a_500(client):
    """Regression: sum() of no rows is int 0, and int has no .quantize() -> HTTP 500."""
    response = await client.get(
        "/api/revenue/by-channel", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["channels"] == []
    assert body["total_revenue"] == "0.00"
    assert body["total_order"] == 0


async def test_orders_without_attribution_show_up_as_unknown(client, db):
    await add_order(db, 1, utc(2026, 1, 5), net_payment="80.00")  # no channel row

    response = await client.get(
        "/api/revenue/by-channel", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
    )

    assert response.json()["channels"][0]["channel"] == "UNKNOWN"


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize("path", REVENUE_ENDPOINTS)
async def test_end_date_before_start_date_is_rejected(client, path):
    response = await client.get(path, params={"start_date": "2026-02-01", "end_date": "2026-01-01"})

    assert response.status_code == 400


@pytest.mark.parametrize("path", REVENUE_ENDPOINTS)
async def test_range_limit_is_730_days_inclusive(client, path):
    ok = await client.get(path, params={"start_date": "2024-01-01", "end_date": "2025-12-31"})
    too_long = await client.get(path, params={"start_date": "2024-01-01", "end_date": "2026-01-01"})

    assert ok.status_code == 200  # exactly 730 days apart
    assert too_long.status_code == 400  # 731 days apart


@pytest.mark.parametrize("path", REVENUE_ENDPOINTS)
async def test_malformed_date_is_a_422_not_a_500(client, path):
    response = await client.get(path, params={"start_date": "not-a-date"})

    assert response.status_code == 422


async def test_summary_amounts_match_between_summary_and_trend(client, january_2026):
    """Two widgets on the same page must never disagree about the same month."""
    params = {"start_date": "2026-01-01", "end_date": "2026-01-31"}
    summary = (await client.get("/api/revenue/summary", params=params)).json()
    trend = (await client.get("/api/revenue/trend", params=params)).json()

    assert Decimal(summary["net_sales"]) == Decimal(trend["current_total_net_sales"])
