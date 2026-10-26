import { useState } from "react";
import DateRangePicker from "../components/DateRangePicker";
import CustomerSummaryCards from "../components/CustomerSummaryCards";
import CustomerRFMChart from "../components/CustomerRFMChart";
import TopCustomersTable from "../components/TopCustomersTable";
import CustomerAcquisitionTrend from "../components/CustomerAcquisitionTrend";
import CohortRetention from "../components/CohortRetention";
import { DEFAULT_START_DATE, DEFAULT_END_DATE } from "../lib/dateDefaults";

function CustomersPage() {
  // Independent date state — tidak share dengan global filter
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

        {/* Date Range Picker (affects: KPI Summary) */}
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />

        {/* KPI Summary (periode-aware) */}
        <CustomerSummaryCards startDate={startDate} endDate={endDate} />

        {/* RFM Segmentation (standalone, lifetime behavior) */}
        <CustomerRFMChart />

        {/* Top Customers (standalone, lifetime value) */}
        <TopCustomersTable limit={10} />

        {/* Acquisition Trend (standalone, 12 months) */}
        <CustomerAcquisitionTrend />

        {/* Cohort Retention (standalone, 12 cohorts × 6 periods) */}
        <CohortRetention />

        {/* Placeholder */}
        <div className="bg-card p-6 rounded-lg border border-subtle text-center text-tertiary">
          <p className="text-sm">🚧 Coming next: Geographic Breakdown</p>
        </div>
      </div>
    </div>
  );
}

export default CustomersPage;
