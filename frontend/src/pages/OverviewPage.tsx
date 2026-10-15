import type { Granularity } from "../components/GranularitySelector";
import RevenueSummaryCards from "../components/RevenueSummaryCards";
import RevenueByChannelChart from "../components/RevenueByChannelChart";
import RevenueTrendChart from "../components/RevenueTrendChart";
import YearlyRevenueComparison from "../components/YearlyRevenueComparisson";
import TopProductsWidget from "../components/TopProductsWidget";
import { useState } from "react";

interface OverviewPageProps {
  startDate: string;
  endDate: string;
}

function OverviewPage({ startDate, endDate }: OverviewPageProps) {
  const [granularity] = useState<Granularity>("day");

  return (
    <>
      {/* KPI STRIP */}
      <div className="px-3 pt-2 flex-none">
        <RevenueSummaryCards startDate={startDate} endDate={endDate} />
      </div>

      {/* MAIN CONTENT GRID */}
      <div className="flex-1 min-h-0 flex flex-col gap-2 px-3 pb-2 pt-2 desk:grid desk:grid-rows-[1fr_1fr]">
        {/* TOP ROW: Revenue Trend + Yearly Revenue */}
        <div className="min-h-0 grid grid-cols-1 md:grid-cols-2 desk:grid-cols-[3fr_2fr] gap-2">
          <div className="h-80 lg:h-96 desk:h-full min-h-0">
            <RevenueTrendChart
              startDate={startDate}
              endDate={endDate}
              granularity={granularity}
            />
          </div>
          <div className="h-80 lg:h-96 desk:h-full min-h-0">
            <YearlyRevenueComparison />
          </div>
        </div>

        {/* BOTTOM ROW: Top Products + Revenue by Channel */}
        <div className="min-h-0 grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-2">
          <div className="h-96 desk:h-full min-h-0 flex flex-col overflow-hidden">
            <TopProductsWidget startDate={startDate} endDate={endDate} />
          </div>
          <div className="h-[28rem] sm:h-80 lg:h-96 desk:h-full min-h-0">
            <RevenueByChannelChart startDate={startDate} endDate={endDate} />
          </div>
        </div>
      </div>
    </>
  );
}

export default OverviewPage;
