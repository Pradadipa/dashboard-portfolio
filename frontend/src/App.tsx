import Header from "./components/Header";
import DateRangePicker from "./components/DateRangePicker";
import GranularitySelector, {type Granularity} from "./components/GranularitySelector";
import RevenueSummaryCards from "./components/RevenueSummaryCards";
import RevenueByChannelChart from "./components/RevenueByChannelChart";
import RevenueTrendChart from "./components/RevenueTrendChart";
import YearlyRevenueComparison from "./components/YearlyRevenueComparisson";
import { useState } from "react";

// Helper function
function formatDate(date: Date) {
  return date.toISOString().split("T")[0];
}

// Default: July 1, 2026 to July 31, 2026
const defaultStartDate = formatDate(new Date("2026-07-01"));
const defaultEndDate = formatDate(new Date("2026-07-31"));

function App() {
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);
  const [granularity, setGranularity ] = useState<Granularity>("day");

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <Header
        title="Business Dashboard"
        subtitle="Real-time revenue metris"
      />

      <DateRangePicker
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />


      <RevenueSummaryCards startDate={startDate} endDate={endDate} />

      <GranularitySelector value={granularity} onChange={setGranularity} />
      <RevenueTrendChart startDate={startDate} endDate={endDate} granularity={granularity} />
      <YearlyRevenueComparison />
      <RevenueByChannelChart startDate={startDate} endDate={endDate} />
    </div>
    </div>
  );
}

export default App;

