from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    TopProductsResponse,
    TopProduct,
    ProductSparklinePoint,
)

async def get_top_products(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        limit: int = 10
) -> TopProductsResponse:
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
        LIMIT :limit
    """)

    top_result = await db.execute(
        top_query,
        {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit
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

    # Create sparkline
    sparkline_query = text("""
        SELECT
            MAX(title) AS product_name,
            date_key AS date,
            SUM(amount) AS revenue
        FROM shopify.v_net_sales_lines
        WHERE title = ANY(:product_titles) AND date_key >= :start_date AND date_key <= :end_date
        GROUP BY title, date
        ORDER BY title, date
    """)

    sparkline_result = await db.execute(
        sparkline_query,
        {
            "product_titles": product_titles,
            "start_date": start_date,
            "end_date": end_date
        }
    )

    sparkline_rows = sparkline_result.all()

    # Build lookup dict
    sparkline_lookup: dict[str, list[ProductSparklinePoint]] = {}
    for row in sparkline_rows:
        point = ProductSparklinePoint(
            date=row.date,
            revenue=Decimal(row.revenue).quantize(Decimal("0.01"))
        )
        if row.product_name not in sparkline_lookup:
            sparkline_lookup[row.product_name] = []
        sparkline_lookup[row.product_name].append(point)

    # Build response
    products = []
    for index, row in enumerate(top_rows):
        products.append(TopProduct(
            rank=index+1,
            product_id=0,
            product_name=row.product_name,
            revenue=Decimal(row.revenue).quantize(Decimal("0.01")),
            units_sold=int(row.units_sold or 0),
            sparkline=sparkline_lookup.get(row.product_name, [])
        ))

    return TopProductsResponse(
        start_date=start_date,
        end_date=end_date,
        products=products,
        total_products_count=len(products),
    )