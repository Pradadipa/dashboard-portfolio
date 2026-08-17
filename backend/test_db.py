import asyncio
from sqlalchemy import text
from app.db.session import engine

async def test_connection():
    print("Testing database connection...")

    async with engine.connect() as conn:
        # Test1: Execute a simple query to check if the connection is working
        result = await conn.execute(text("SELECT 1"))
        row=result.one()
        print(f"Test 1 passed: {row[0]}")

        # Test2
        result=await conn.execute(text("SELECT version()"))
        version=result.scalar()
        print(f"PostgreSQL: {version[:60]}...")

        # Test3
        result=await conn.execute(text("""
        SELECT COUNT(*)
        FROM information_schema.schemata
        WHERE schema_name = 'shopify'
        """))
        count=result.scalar()
        print(f"Schema 'shopify' exists: {count == 1}")

        # Test4
        result=await conn.execute(text("""
        SELECT COUNT(*) FROM shopify.orders
        """))
        ordert_count = result.scalar()
        print(f"shopify.orders table has {ordert_count} rows.")

        # Test5
        result=await conn.execute(text("""
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN row_type = 'SALE' THEN 1 ELSE 0 END) AS sale_rows,
            SUM(CASE WHEN row_type = 'RETURN' THEN 1 ELSE 0 END) AS return_rows
        FROM shopify.v_net_sales_lines
        """))
        row = result.one()
        print(f"Total rows: {row.total_rows}, Sale rows: {row.sale_rows}, Return rows: {row.return_rows}")

    print("Database connection test completed.")

    await engine.dispose()  # Dispose of the engine to close all connections

if __name__ == "__main__":
    asyncio.run(test_connection())