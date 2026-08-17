import asyncio
from datetime import date, timedelta
from app.db.session import AsyncSessionLocal, engine
from app.services.revenue_services import get_revenue_summary

async def main():
    # Create session
    async with AsyncSessionLocal() as session:
        # Get 30 days data
        end_date = date(2026,4,30)
        start_date = end_date - timedelta(days=30)

        print(f"Period: {start_date} - {end_date}")
        print()
        summary = await get_revenue_summary(session, start_date, end_date)

        # Print as json
        print("Revenue Summary")
        print(summary.model_dump_json(indent=2))

        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())