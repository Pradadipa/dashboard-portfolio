import Sidebar, { type Page } from "./components/Sidebar";
import Header from "./components/Header";
import DateRangePicker from "./components/DateRangePicker";
import type { Granularity } from "./components/GranularitySelector";
import RevenueSummaryCards from "./components/RevenueSummaryCards";
import RevenueByChannelChart from "./components/RevenueByChannelChart";
import RevenueTrendChart from "./components/RevenueTrendChart";
import YearlyRevenueComparison from "./components/YearlyRevenueComparisson";
import TopProductsWidget from "./components/TopProductsWidget";
import CustomersPage from "./components/CustomersPage";
import { useState } from "react";
import { PanelLeft } from "lucide-react";

// Helper function
function formatDate(date: Date) {
  return date.toISOString().split("T")[0];
}

// Same breakpoint as the `desk` variant in index.css: one-screen layout, sidebar open by default.
const DESK_QUERY = "(min-width: 1280px) and (min-height: 720px)";

// Default: July 1, 2026 to July 31, 2026
const defaultStartDate = formatDate(new Date("2026-07-01"));
const defaultEndDate = formatDate(new Date("2026-07-31"));

// Temporary placeholder
// function PlaceholderBox({ label, color } : {label:string; color: string}) {
//   return (
//     <div className={`h-full w-full min-h-0 rounded-lg shadow flex items-center justify-center text-white font-semibold ${color}`}>
//       {label}
//     </div>
//   );
// }

function App() {
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);
  const [granularity] = useState<Granularity>("day");
  // Desktop: sidebar terbuka di awal. HP/tablet: tertutup (dibuka sebagai drawer).
  const [sidebarOpen, setSidebarOpen] = useState(() => window.matchMedia(DESK_QUERY).matches);
  const [page, setPage] = useState<Page>("overview");

  function navigate(next: Page) {
    setPage(next);
    // HP/tablet: tutup drawer setelah pindah halaman.
    if (!window.matchMedia(DESK_QUERY).matches) setSidebarOpen(false);
  }

  return (
    // desk (>=1280x720, lihat index.css): h-screen = tinggi persis viewport, semua widget muat 1 layar.
    // HP/tablet/laptop pendek: tinggi bebas, halaman di-scroll, chart bertinggi tetap.
    <div className="min-h-screen desk:h-screen flex desk:overflow-hidden" style={{ backgroundColor: 'var(--bg-page)' }}>

      {/* SIDEBAR — desk: kolom statis yang bisa ditutup; di bawah desk: drawer */}
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activePage={page}
        onNavigate={navigate}
      />

      {/* KOLOM KANAN — sisa lebar, flex-col seperti sebelumnya */}
      <div className="flex-1 min-w-0 flex flex-col desk:overflow-hidden">

        {/* BAR ATAS — flex-none = tinggi natural, gak ikut dikompres */}
        <div className="flex-none flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-kpi-card border-b border-subtle shadow-sm">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
              aria-expanded={sidebarOpen}
              className="flex-none p-2 rounded-lg text-secondary hover:text-primary hover:bg-card-hover transition-colors"
            >
              <PanelLeft size={18} />
            </button>
            <Header
              title="Good morning, Prada 🖐"
              subtitle="Here's what happening with your business"
            />
          </div>
          <DateRangePicker
            startDate={startDate}
            endDate={endDate}
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
          />
        </div>

        {page === "customers" ? (
          <div className="flex-1 min-h-0 p-3">
            <CustomersPage />
          </div>
        ) : (
        <>
        {/* KPI STRIP — flex-none juga, tinggi natural (5 card sejajar) */}
        <div className="px-3 pt-2 flex-none">
          <RevenueSummaryCards startDate={startDate} endDate={endDate} />
        </div>

         {/* SISA RUANG — desk: flex-1 = "ambil semua sisa tinggi", min-h-0 = "boleh dikompres, jangan maksa ukuran alami".
             Di bawah desk tiap widget dapat tinggi tetap (h-80 dst.) karena chart butuh parent bertinggi pasti. */}
        <div className="flex-1 min-h-0 flex flex-col gap-2 px-3 pb-2 pt-2 desk:grid desk:grid-rows-[1fr_1fr]">

          {/* BARIS ATAS: Revenue Trend bersebelahan dengan Yearly Revenue (tablet: 2 kolom sama lebar, HP: ditumpuk) */}
          <div className="min-h-0 grid grid-cols-1 md:grid-cols-2 desk:grid-cols-[3fr_2fr] gap-2">
            <div className="h-80 lg:h-96 desk:h-full min-h-0">
              <RevenueTrendChart startDate={startDate} endDate={endDate} granularity={granularity} />
            </div>
            <div className="h-80 lg:h-96 desk:h-full min-h-0">
              <YearlyRevenueComparison />
            </div>
          </div>

          {/* BARIS BAWAH: Top Products bersebelahan dengan Revenue by Channel (ditumpuk di bawah lg) */}
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
        )}
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

