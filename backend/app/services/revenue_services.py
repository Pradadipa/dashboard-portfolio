from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.revenue import RevenueSummary

async def get_revenue_summary(
        db: AsyncSession,
        start_date: date,
        end_date: date,
) -> RevenueSummary:
    """
    Get revenue summary for a given date range.
    
    Args:
        db (AsyncSession): SQLAlchemy async session.
        start_date (date): Start date of the period.
        end_date (date): End date of the period.
    
    Returns:
        RevenueSummary: Summary of revenue metrics.
    """
    query = text("""
        SELECT
            COALESCE(SUM(CASE WHEN row_type = 'SALE' THEN amount ELSE 0 END), 0) AS total_sales,
            COALESCE(SUM(CASE WHEN row_type = 'RETURN' THEN amount ELSE 0 END), 0) AS total_returns_negative,
            COALESCE(SUM(amount), 0) AS net_sales,
            COALESCE(COUNT(DISTINCT CASE WHEN row_type = 'SALE' THEN order_id END), 0) AS total_orders
        FROM 
            shopify.v_net_sales_lines
        WHERE 
            date_key >= :start_date AND date_key <= :end_date
    """)

    result = await db.execute(query, {'start_date': start_date, 'end_date': end_date})
    row = result.one()

    # Convert DB to Decimal
    total_sales = Decimal(row.total_sales)
    total_returns = abs(Decimal(row.total_returns_negative))  # Ensure refunds are positive
    net_sales = Decimal(row.net_sales)
    total_orders = row.total_orders or 0  # Default to 0 if None

    # Calculate average order value, handling division by zero
    aov = (net_sales / total_orders) if total_orders > 0 else Decimal('0.00')

    # Return the revenue summary as a Pydantic model
    return RevenueSummary(
        start_date=start_date,
        end_date=end_date,
        total_sales=total_sales.quantize(Decimal('0.01')),  # Round to 2 decimal places
        total_returns=total_returns.quantize(Decimal('0.01')),  # Round to 2 decimal places
        net_sales=net_sales.quantize(Decimal('0.01')),  # Round to 2 decimal places
        total_orders=total_orders,
        average_order_value=aov.quantize(Decimal('0.01')),  # Round to 2 decimal places
        currency='USD'  # Assuming USD; adjust as necessary
    )
