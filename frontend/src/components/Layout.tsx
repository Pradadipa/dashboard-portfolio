import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import DateRangePicker from "./DateRangePicker";
import { PanelLeft } from "lucide-react";

const DESK_QUERY = "(min-width: 1280px) and (min-height: 720px)";

interface LayoutProps {
  // Global filter state (shared across pages that opt in)
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
}

function Layout({ startDate, endDate, onStartDateChange, onEndDateChange }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.matchMedia(DESK_QUERY).matches);
  const location = useLocation();

  // Pages yang punya date filter sendiri (independent) — hide global picker
  const PAGES_WITH_OWN_FILTER = ["/customers"];
  const showGlobalFilter = !PAGES_WITH_OWN_FILTER.includes(location.pathname);

  // Close sidebar after navigation on mobile
  function handleSidebarClose() {
    setSidebarOpen(false);
  }

  return (
    <div
      className="min-h-screen desk:h-screen flex desk:overflow-hidden"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* SIDEBAR */}
      <Sidebar
        open={sidebarOpen}
        onClose={handleSidebarClose}
        onNavigate={() => {
          // On mobile, close drawer after navigation
          if (!window.matchMedia(DESK_QUERY).matches) setSidebarOpen(false);
        }}
      />

      {/* MAIN AREA */}
      <div className="flex-1 min-w-0 flex flex-col desk:overflow-hidden">
        {/* TOP BAR */}
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
          {showGlobalFilter && (
            <DateRangePicker
              startDate={startDate}
              endDate={endDate}
              onStartDateChange={onStartDateChange}
              onEndDateChange={onEndDateChange}
            />
          )}
        </div>

        {/* ROUTED CONTENT */}
        <Outlet />
      </div>
    </div>
  );
}

export default Layout;
