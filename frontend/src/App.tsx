import { Routes, Route } from "react-router-dom";
import { useState } from "react";
import Layout from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import CustomersPage from "./pages/CustomersPage";
import { DEFAULT_START_DATE, DEFAULT_END_DATE } from "./lib/dateDefaults";

function App() {
  // Global date filter state (shared across pages via Layout)
  const [startDate, setStartDate] = useState(DEFAULT_START_DATE);
  const [endDate, setEndDate] = useState(DEFAULT_END_DATE);

  return (
    <Routes>
      <Route
        path="/"
        element={
          <Layout
            startDate={startDate}
            endDate={endDate}
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
          />
        }
      >
        {/* Overview: pakai global date filter */}
        <Route
          index
          element={<OverviewPage startDate={startDate} endDate={endDate} />}
        />

        {/* Customers: pakai internal date filter sendiri */}
        <Route path="customers" element={<CustomersPage />} />
      </Route>
    </Routes>
  );
}

export default App;
