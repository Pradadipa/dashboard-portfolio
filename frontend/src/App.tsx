import Header from "./components/Header";
import RevenueSummaryCards from "./components/RevenueSummaryCards";
import RevenueByChannelChart from "./components/RevenueByChannelChart";
import RevenueTrendChart from "./components/RevenueTrendChart";

function App() {
  return (
    <div>
      <Header
        title="Business Dashboard"
        subtitle="Real-time revenue metris"
      />
      <hr />
      <RevenueSummaryCards />
      <hr />
      <RevenueTrendChart />
      <hr />
      <RevenueByChannelChart />
    </div>
  );
}

export default App;

