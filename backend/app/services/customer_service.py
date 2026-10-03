from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.customer import CustomerSummary

async def get_customer_summary(
        db: AsyncSession,
        start_date: date,
        end_date: date
) -> CustomerSummary:
    counts_query = text("""
        WITH active_customers AS (
            SELECT DISTINCT c.customer_id, c.customer_since
            FROM shopify.customers c
            JOIN 
        )
    """)