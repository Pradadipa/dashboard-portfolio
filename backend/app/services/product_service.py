from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

def calc_change_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    """
    Hitung % change vs previous.
    Return None kalau previous = 0 (tidak bisa hitung growth).
    """
    if previous == 0:
        return None
    change = ((current - previous) / previous) * 100
    return change.quantize(Decimal("0.01"))

from app.schemas.product import (
    TopProductsResponse,
    TopProduct,
)

async def get_top_products(
        db: AsyncSession,
        start_date: date,
        end_date: date,
) -> TopProductsResponse:

    period_length = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    top_query = text("""
        SELECT
            title AS product_name,
            SUM(amount) AS revenue,
            SUM(quantity) AS units_sold
        FROM shopify.v_net_sales_lines
        WHERE date_key >= :start_date AND date_key <= :end_date
        GROUP BY title
        HAVING SUM(amount) > 0
        ORDER BY revenue DESC
    """)

    top_result = await db.execute(
        top_query,
        {
            "start_date": start_date,
            "end_date": end_date,
        }
    )
    top_rows = top_result.all()

    if not top_rows:
        return TopProductsResponse(
            start_date=start_date,
            end_date=end_date,
            products=[],
            total_products_count=0
        )
    # Extract titles untuk sparkline query
    product_titles = [row.product_name for row in top_rows]

    previous_query = text("""
        SELECT
            title AS product_name,
            COALESCE(SUM(amount), 0) AS revenue,
            COALESCE(SUM(quantity), 0) AS units_sold
        FROM shopify.v_net_sales_lines
        WHERE date_key >= :start_date
            AND date_key <= :end_date
            AND title = ANY(:product_titles)
        GROUP BY title
    """)

    previous_result = await db.execute(
        previous_query,
        {
            "start_date": previous_start,
            "end_date": previous_end,
            "product_titles": product_titles
        }
    )

    previous_rows = previous_result.all()

    # Build lookup
    previous_lookup: dict[str, dict] = {}
    for row in previous_rows:
        previous_lookup[row.product_name] = {
            'revenue': Decimal(row.revenue),
            'units_sold': int(row.units_sold or 0)
        }


    # Build response
    products = []
    for index, row in enumerate(top_rows):
        current_revenue = Decimal(row.revenue)
        current_units = int(row.units_sold or 0)

        previous_data = previous_lookup.get(row.product_name, {
            'revenue': Decimal("0"),
            'units_sold': 0
        })
        previous_revenue = previous_data['revenue']
        previous_units = previous_data['units_sold']

        # Calc change % (pakai helper function)
        revenue_change = calc_change_percent(current_revenue, previous_revenue)
        units_change = calc_change_percent(
            Decimal(current_units),
            Decimal(previous_units),
        ) 
        products.append(TopProduct(
                rank=index + 1,
                product_id=0,
                product_name=row.product_name,
                revenue=current_revenue.quantize(Decimal("0.01")),
                units_sold=current_units,
                previous_revenue=previous_revenue.quantize(Decimal("0.01")),
                previous_units_sold=previous_units,
                revenue_change_percent=revenue_change,
                units_change_percent=units_change,
            ))

    return TopProductsResponse(
        start_date=start_date,
        end_date=end_date,
        products=products,
        total_products_count=len(products),
    )