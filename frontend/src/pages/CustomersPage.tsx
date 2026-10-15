import { useState } from "react";
import DateRangePicker from "../components/DateRangePicker";
import CustomerSummaryCards from "../components/CustomerSummaryCards";
import CustomerSegmentationChart from "../components/CustomerSegmentationChart";
import { DEFAULT_START_DATE, DEFAULT_END_DATE } from "../lib/dateDefaults";

function CustomersPage() {
  // Independent date state — tidak share dengan global filter, tapi default-nya sama dengan Overview
  const [startDate, setStartDate] = useState(DEFAULT_START_DATE);
  const [endDate, setEndDate] = useState(DEFAULT_END_DATE);

  return (
    <div className="flex-1 min-h-0 overflow-auto p-3">
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-primary">Customers</h1>
          <p className="text-sm text-secondary mt-1">
            Customer insights, segmentation, dan behavior analysis
          </p>
        </div>

        {/* Independent Date Range Picker */}
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />

        {/* KPI Summary */}
        <CustomerSummaryCards startDate={startDate} endDate={endDate} />

        {/* NEW: Segmentation Chart (New vs Returning) */}
        <CustomerSegmentationChart startDate={startDate} endDate={endDate} />

        {/* Placeholder */}
        <div className="bg-card p-6 rounded-lg border border-subtle text-center text-tertiary">
          <p className="text-sm">🚧 Coming next: Top Customers, Geographic, Trend</p>
        </div>
      </div>
    </div>
  );
}

export default CustomersPage;
