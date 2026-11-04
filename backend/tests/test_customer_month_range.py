"""
Tests for the month range on /acquisition-trend and /cohort-retention.

Both endpoints take the same start_date/end_date as /summary and /rfm. The Customers page
sends whole months, so the range covers every month touched by those two dates.
"""

from tests.factories import add_customer, utc

MAY_TO_JULY = {"start_date": "2026-05-01", "end_date": "2026-07-31"}
WHOLE_DATASET = {"start_date": "2017-10-01", "end_date": "2026-07-31"}
REVERSED = {"start_date": "2026-07-01", "end_date": "2026-05-31"}


async def test_trend_returns_each_month_in_range(client):
    response = await client.get("/api/customers/acquisition-trend", params=MAY_TO_JULY)

    assert response.status_code == 200
    body = response.json()
    assert [p["month"] for p in body["data_points"]] == ["2026-05", "2026-06", "2026-07"]
    assert (body["start_month"], body["end_month"]) == ("2026-05", "2026-07")


async def test_trend_range_can_cross_a_year(client):
    response = await client.get(
        "/api/customers/acquisition-trend",
        params={"start_date": "2025-11-01", "end_date": "2026-02-28"},
    )

    assert [p["month"] for p in response.json()["data_points"]] == [
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
    ]


async def test_trend_accepts_the_whole_dataset(client):
    response = await client.get("/api/customers/acquisition-trend", params=WHOLE_DATASET)

    assert response.status_code == 200
    assert len(response.json()["data_points"]) == 106


async def test_cohort_lists_only_cohorts_in_range(db, client):
    await add_customer(db, 1, utc(2026, 4, 15))  # before the range
    await add_customer(db, 2, utc(2026, 5, 15))
    await add_customer(db, 3, utc(2026, 7, 15))

    response = await client.get("/api/customers/cohort-retention", params=MAY_TO_JULY)

    assert response.status_code == 200
    assert [r["cohort_month"] for r in response.json()["rows"]] == ["2026-05-01", "2026-07-01"]


async def test_cohort_accepts_the_whole_dataset(db, client):
    await add_customer(db, 1, utc(2017, 10, 28))

    response = await client.get("/api/customers/cohort-retention", params=WHOLE_DATASET)

    assert response.status_code == 200
    assert [r["cohort_month"] for r in response.json()["rows"]] == ["2017-10-01"]


async def test_trend_rejects_reversed_range(client):
    response = await client.get("/api/customers/acquisition-trend", params=REVERSED)

    assert response.status_code == 400


async def test_cohort_rejects_reversed_range(client):
    response = await client.get("/api/customers/cohort-retention", params=REVERSED)

    assert response.status_code == 400
