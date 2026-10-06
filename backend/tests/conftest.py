"""
Shared test setup.

SAFETY: the `clean_db` fixture TRUNCATEs tables before every test. To make sure this
can never wipe your dev or real data, the whole test run aborts unless the target
database name ends with "_test".

The test database must already contain the schema and migrations:

    psql "$PGURL" -v ON_ERROR_STOP=1 -f ../db/schema.sql
    uv run alembic upgrade head

CI does exactly these two steps before it runs pytest. Locally, point the tests at a
throw-away database (the default dev database is NOT accepted):

    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/dashboard_test uv run pytest

Without TEST_DATABASE_URL, DATABASE_URL from the environment is used (that is what CI sets).
"""

import os
from urllib.parse import urlparse

import pytest
import pytest_asyncio

from tests import factories


def _resolve_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.exit(
            "No test database configured. Set TEST_DATABASE_URL "
            "(e.g. postgresql+asyncpg://user:pass@localhost:5432/dashboard_test).",
            returncode=2,
        )
    db_name = urlparse(url).path.lstrip("/")
    if not db_name.endswith("_test"):
        pytest.exit(
            f"Refusing to run: database '{db_name}' does not end with '_test'. "
            "Tests TRUNCATE tables, so they only run against a dedicated test database.",
            returncode=2,
        )
    return url


# This MUST run before the first `import app...` anywhere: Settings() and the async engine
# are created at import time, and an environment variable beats backend/.env
# (which normally points at your dev database).
os.environ["DATABASE_URL"] = _resolve_test_database_url()

REQUIRED_RELATIONS = [
    "shopify.orders",
    "shopify.order_line_items",
    "shopify.refund_line_items",
    "shopify.order_attribution",
    "shopify.v_net_sales_lines",
    "shopify.v_daily_sales_by_channel",
    "public.annotations",
]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database_is_ready():
    """Fail once, with a useful message, if schema.sql / alembic were not applied."""
    from sqlalchemy import text

    from app.db.session import engine

    async with engine.connect() as conn:
        missing = []
        for relation in REQUIRED_RELATIONS:
            found = await conn.scalar(text("SELECT to_regclass(:name)"), {"name": relation})
            if found is None:
                missing.append(relation)
    if missing:
        pytest.exit(
            f"Test database is missing {missing}. Apply db/schema.sql and "
            "`alembic upgrade head` first (see tests/conftest.py).",
            returncode=2,
        )
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(_database_is_ready):
    """Every test starts from empty tables, so tests cannot influence each other."""
    from sqlalchemy import text

    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE shopify.refund_line_items, shopify.order_line_items, "
                "shopify.order_attribution, shopify.orders, shopify.customers, "
                "public.annotations RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def db():
    """A database session for seeding data and for calling services directly."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """HTTP client that talks to the FastAPI app in-process (no server needed)."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def january_2026(db):
    """The hand-checkable dataset described in tests/factories.py."""
    await factories.seed_january_2026(db)
