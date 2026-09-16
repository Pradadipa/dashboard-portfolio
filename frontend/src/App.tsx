import Sidebar from "./components/Sidebar";
import DateRangePicker from "./components/DateRangePicker";
import GranularitySelector, {type Granularity} from "./components/GranularitySelector";
import RevenueSummaryCards from "./components/RevenueSummaryCards";
import RevenueByChannelChart from "./components/RevenueByChannelChart";
import RevenueTrendChart from "./components/RevenueTrendChart";
import YearlyRevenueComparison from "./components/YearlyRevenueComparisson";
import TopProductsWidget from "./components/TopProductsWidget";
import { useState } from "react";

// Helper function
function formatDate(date: Date) {
  return date.toISOString().split("T")[0];
}

// Default: July 1, 2026 to July 31, 2026
const defaultStartDate = formatDate(new Date("2026-07-01"));
const defaultEndDate = formatDate(new Date("2026-07-31"));

// Temporary placeholder
function PlaceholderBox({ label, color } : {label:string; color: string}) {
  return (
    <div className={`h-full w-full min-h-0 rounded-lg shadow flex items-center justify-center text-white font-semibold ${color}`}>
      {label}
    </div>
  );
}

function App() {
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);
  const [granularity, setGranularity ] = useState<Granularity>("day");

  return (
    // h-screen = tinggi persis viewport; flex-row = sidebar kiri + konten kanan
    <div className="h-screen flex overflow-hidden bg-gray-50">

      {/* SIDEBAR — flex-none, lebar tetap */}
      <Sidebar />

      {/* KOLOM KANAN — sisa lebar, flex-col seperti sebelumnya */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">

        {/* BAR ATAS — flex-none = tinggi natural, gak ikut dikompres */}
        <div className="flex-none flex items-center justify-end gap-2 px-3 py-1.5 bg-white shadow-sm">
          <DateRangePicker
            startDate={startDate}
            endDate={endDate}
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
          />
        </div>

        {/* KPI STRIP — flex-none juga, tinggi natural (5 card sejajar) */}
        <div className="px-3 pt-2 flex-none">
          <RevenueSummaryCards startDate={startDate} endDate={endDate} />
        </div>

         {/* SISA RUANG — flex-1 = "ambil semua sisa tinggi", min-h-0 = "boleh dikompres, jangan maksa ukuran alami" */}
        <div className="flex-1 min-h-0 grid grid-rows-[1fr_1fr] gap-2 px-3 pb-2 pt-2">

          {/* BARIS ATAS: Revenue Trend (1) bersebelahan dengan Revenue Overview (1) */}
          <div className="min-h-0 grid grid-cols-[3fr_2fr] gap-2">
            <RevenueTrendChart startDate={startDate} endDate={endDate} granularity={granularity} />
            <YearlyRevenueComparison />
          </div>

          {/* BARIS BAWAH: Top Products (2) bersebelahan dengan Revenue by Channel (1) */}
          <div className="min-h-0 grid grid-cols-[1fr_1fr] gap-2">
            <div className="min-h-0 bg-white rounded-lg shadow p-2">
              <TopProductsWidget startDate={startDate} endDate={endDate} />
            </div>
            <RevenueByChannelChart startDate={startDate} endDate={endDate} />
          </div>
        </div>
      </div>
    </div>
    // <div className="min-h-screen bg-gray-50">
    //   <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
    //   <Header
    //     title="Business Dashboard"
    //     subtitle="Real-time revenue metris"
    //   />

    //   <DateRangePicker
    //     startDate={startDate}
    //     endDate={endDate}
    //     onStartDateChange={setStartDate}
    //     onEndDateChange={setEndDate}
    //   />


    //   <RevenueSummaryCards startDate={startDate} endDate={endDate} />

    //   <GranularitySelector value={granularity} onChange={setGranularity} />
    //   <RevenueTrendChart startDate={startDate} endDate={endDate} granularity={granularity} />
    //   <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    //     <YearlyRevenueComparison />
    //     <RevenueByChannelChart startDate={startDate} endDate={endDate} />
    //   </div>
    //   <TopProductsWidget startDate={startDate} endDate={endDate} />
    // </div>
    // </div>
  );
}

export default App;

