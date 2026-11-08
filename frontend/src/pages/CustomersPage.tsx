import { useState } from "react";
import MonthRangePicker from "../components/MonthRangePicker";
import CustomerSummaryCards from "../components/CustomerSummaryCards";
import CustomerRFMChart from "../components/CustomerRFMChart";
import TopCustomersTable from "../components/TopCustomersTable";
import CustomerAcquisitionTrend from "../components/CustomerAcquisitionTrend";
import CohortRetention from "../components/CohortRetention";
import AcquisitionChannelQuality from "../components/AcquisitionChannelQuality";
import {
  CUSTOMERS_DEFAULT_START_MONTH,
  CUSTOMERS_DEFAULT_END_MONTH,
  CUSTOMERS_FIRST_MONTH,
  CUSTOMERS_LAST_MONTH,
} from "../lib/dateDefaults";
import { firstDayOfMonth, lastDayOfMonth } from "../lib/monthRange";

function CustomersPage() {
  // Independent month state — tidak share dengan global filter
  const [startMonth, setStartMonth] = useState(CUSTOMERS_DEFAULT_START_MONTH);
  const [endMonth, setEndMonth] = useState(CUSTOMERS_DEFAULT_END_MONTH);

  const startDate = firstDayOfMonth(startMonth);
  const endDate = lastDayOfMonth(endMonth);

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

        {/* Month Range Picker (affects: KPI Summary, RFM Segmentation, Acquisition Trend, Cohort Retention) */}
        <MonthRangePicker
          startMonth={startMonth}
          endMonth={endMonth}
          firstMonth={CUSTOMERS_FIRST_MONTH}
          lastMonth={CUSTOMERS_LAST_MONTH}
          onChange={(start, end) => {
            setStartMonth(start);
            setEndMonth(end);
          }}
        />

        {/* KPI Summary (periode-aware) */}
        <CustomerSummaryCards startDate={startDate} endDate={endDate} />

        {/* RFM Segmentation (customers periode-aware, label dari lifetime behavior) */}
        <CustomerRFMChart startDate={startDate} endDate={endDate} />

        {/* Top Customers (standalone, lifetime value) */}
        <TopCustomersTable limit={10} />

        {/* Acquisition Trend (periode-aware, per bulan) */}
        <CustomerAcquisitionTrend startDate={startDate} endDate={endDate} />

        {/* Cohort Retention (periode-aware, cohort dalam range × 6 periods) */}
        <CohortRetention startDate={startDate} endDate={endDate} />

        {/* Acquisition Channel Quality (standalone, cohort 180-90 hari sebelum report end) */}
        <AcquisitionChannelQuality />

        {/* Placeholder */}
        <div className="bg-card p-6 rounded-lg border border-subtle text-center text-tertiary">
          <p className="text-sm">🚧 Coming next: Geographic Breakdown</p>
        </div>
      </div>
    </div>
  );
}

export default CustomersPage;
