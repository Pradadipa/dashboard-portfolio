"""HTTP-level tests for /api/annotations (create, get, list + filters, validation)."""

import pytest
from sqlalchemy import text


async def _create(client, **overrides):
    payload = {"date": "2026-03-15", "title": "Black Friday", "category": "campaign"}
    payload.update(overrides)
    return await client.post("/api/annotations", json=payload)


async def test_create_returns_201_and_the_saved_annotation(client):
    response = await _create(client, created_by="prada")

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["date"] == "2026-03-15"
    assert body["title"] == "Black Friday"
    assert body["category"] == "campaign"
    assert body["created_by"] == "prada"
    assert body["created_at"] and body["updated_at"]  # filled in by the database


async def test_create_defaults_category_to_other(client):
    response = await client.post("/api/annotations", json={"date": "2026-03-15", "title": "Note"})

    assert response.status_code == 201
    assert response.json()["category"] == "other"


async def test_description_is_stored_in_the_database(client, db):
    await _create(client, description="50% off for 3 days")

    stored = await db.scalar(text("SELECT description FROM annotations WHERE id = 1"))

    assert stored == "50% off for 3 days"


async def test_get_by_id(client):
    created = (await _create(client)).json()

    response = await client.get(f"/api/annotations/{created['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Black Friday"


async def test_get_unknown_id_is_404(client):
    response = await client.get("/api/annotations/999")

    assert response.status_code == 404


async def test_list_is_newest_first_and_reports_total(client):
    await _create(client, date="2026-01-01", title="first")
    await _create(client, date="2026-03-01", title="third")
    await _create(client, date="2026-02-01", title="second")

    body = (await client.get("/api/annotations")).json()

    assert body["total"] == 3
    assert [a["title"] for a in body["annotations"]] == ["third", "second", "first"]


async def test_list_same_day_puts_the_latest_created_first(client):
    await _create(client, date="2026-03-01", title="morning")
    await _create(client, date="2026-03-01", title="evening")

    body = (await client.get("/api/annotations")).json()

    assert [a["title"] for a in body["annotations"]] == ["evening", "morning"]


async def test_list_filters_by_category(client):
    await _create(client, title="promo", category="promotion")
    await _create(client, title="outage", category="incident")

    body = (await client.get("/api/annotations", params={"category": "incident"})).json()

    assert body["total"] == 1
    assert body["annotations"][0]["title"] == "outage"


async def test_list_date_filter_is_inclusive_on_both_ends(client):
    for day in ("2026-03-01", "2026-03-10", "2026-03-20", "2026-03-31"):
        await _create(client, date=day, title=day)

    body = (
        await client.get(
            "/api/annotations", params={"start_date": "2026-03-10", "end_date": "2026-03-20"}
        )
    ).json()

    assert sorted(a["date"] for a in body["annotations"]) == ["2026-03-10", "2026-03-20"]
    assert body["total"] == 2


async def test_list_on_empty_database(client):
    body = (await client.get("/api/annotations")).json()

    assert body == {"annotations": [], "total": 0}


async def test_list_end_before_start_is_400(client):
    response = await client.get(
        "/api/annotations", params={"start_date": "2026-03-20", "end_date": "2026-03-10"}
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "bad_payload",
    [
        {"title": "no date"},
        {"date": "2026-03-15"},  # no title
        {"date": "2026-03-15", "title": ""},
        {"date": "2026-03-15", "title": "x" * 201},
        {"date": "2026-03-15", "title": "ok", "description": "x" * 201},
        {"date": "2026-03-15", "title": "ok", "category": "party"},
        {"date": "15-03-2026", "title": "ok"},
    ],
    ids=[
        "missing-date",
        "missing-title",
        "empty-title",
        "title-too-long",
        "description-too-long",
        "unknown-category",
        "bad-date-format",
    ],
)
async def test_create_rejects_invalid_payload(client, bad_payload):
    response = await client.post("/api/annotations", json=bad_payload)

    assert response.status_code == 422
